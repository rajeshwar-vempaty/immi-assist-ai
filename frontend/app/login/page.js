"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getAuthConfig,
  loginWithGoogle,
  loginWithPassword,
  registerAccount,
} from "../../lib/api";
import { useAuth } from "../../lib/auth";

function waitForGoogle(timeoutMs = 8000) {
  return new Promise((resolve, reject) => {
    if (typeof window !== "undefined" && window.google?.accounts?.id) {
      resolve(window.google);
      return;
    }
    const started = Date.now();
    const timer = setInterval(() => {
      if (window.google?.accounts?.id) {
        clearInterval(timer);
        resolve(window.google);
      } else if (Date.now() - started > timeoutMs) {
        clearInterval(timer);
        reject(new Error("Google Identity Services failed to load"));
      }
    }, 100);
  });
}

export default function LoginPage() {
  const { user, loading, setUser, refresh } = useAuth();
  const router = useRouter();
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState("login"); // login | register
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const googleBtn = useRef(null);

  useEffect(() => {
    getAuthConfig()
      .then(setConfig)
      .catch(() => setConfig({ google_client_id: null, password_auth_enabled: true }));
  }, []);

  useEffect(() => {
    if (!loading && user) router.replace("/");
  }, [user, loading, router]);

  useEffect(() => {
    let cancelled = false;
    if (!config?.google_client_id || !googleBtn.current) return undefined;

    (async () => {
      try {
        await waitForGoogle();
        if (cancelled || !googleBtn.current) return;
        window.google.accounts.id.initialize({
          client_id: config.google_client_id,
          callback: async (response) => {
            setBusy(true);
            setError(null);
            try {
              const data = await loginWithGoogle(response.credential);
              setUser(data.user);
              await refresh();
              router.replace("/");
            } catch (err) {
              setError(err.message || "Google login failed");
            } finally {
              setBusy(false);
            }
          },
        });
        googleBtn.current.innerHTML = "";
        window.google.accounts.id.renderButton(googleBtn.current, {
          theme: "outline",
          size: "large",
          width: 320,
          text: "continue_with",
          shape: "rectangular",
        });
      } catch (err) {
        if (!cancelled) setError(err.message || "Could not initialize Google sign-in");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [config, router, setUser, refresh]);

  const finishAuth = async (data) => {
    setUser(data.user);
    await refresh();
    router.replace("/");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === "register") {
        if (password !== confirmPassword) {
          setError("Passwords do not match.");
          return;
        }
        const data = await registerAccount({ username, email, password });
        if (data.welcome_email?.sent) {
          setNotice("Account created. A welcome summary was sent to your email.");
        } else {
          setNotice(
            "Account created. A welcome summary was prepared for your email (configure SMTP to deliver it)."
          );
        }
        await finishAuth(data);
      } else {
        const data = await loginWithPassword({ email, password });
        await finishAuth(data);
      }
    } catch (err) {
      setError(err.message || (mode === "register" ? "Registration failed" : "Sign-in failed"));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="login-shell">
        <div className="login-card">
          <p style={{ color: "var(--muted)" }}>Checking session…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="brand-mark" style={{ marginBottom: 18 }}>
          <div className="mark">IA</div>
          <div>
            <h1>ImmiAssist</h1>
            <p>Sign in to continue</p>
          </div>
        </div>
        <h2 className="login-title">Welcome</h2>
        <p className="login-sub">
          Continue with Google, or create an account with your email. Your chat history and API keys
          stay private to your account.
        </p>

        {error && <div className="error-banner">{error}</div>}
        {notice && (
          <div className="error-banner" style={{ background: "rgba(15, 118, 110, 0.12)", color: "var(--ink)" }}>
            {notice}
          </div>
        )}

        {config?.google_client_id ? (
          <div ref={googleBtn} style={{ display: "flex", justifyContent: "center", minHeight: 44 }} />
        ) : (
          <p className="disclaimer">
            Google Client ID is not configured. You can still register with email below.
          </p>
        )}

        <div className="auth-divider">
          <span>or</span>
        </div>

        <div className="auth-tabs" role="tablist" aria-label="Account">
          <button
            type="button"
            className={`auth-tab ${mode === "login" ? "active" : ""}`}
            onClick={() => setMode("login")}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === "register" ? "active" : ""}`}
            onClick={() => setMode("register")}
          >
            Create account
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ marginTop: 12 }}>
          {mode === "register" && (
            <input
              className="field"
              style={{ marginBottom: 8 }}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              autoComplete="username"
              required
              minLength={2}
            />
          )}
          <input
            className="field"
            type="email"
            style={{ marginBottom: 8 }}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            autoComplete="email"
            required
          />
          <input
            className="field"
            type="password"
            style={{ marginBottom: mode === "register" ? 8 : 10 }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            required
            minLength={8}
          />
          {mode === "register" && (
            <input
              className="field"
              type="password"
              style={{ marginBottom: 10 }}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm password"
              autoComplete="new-password"
              required
              minLength={8}
            />
          )}
          <button className="btn btn-primary" style={{ width: "100%" }} disabled={busy}>
            {busy
              ? mode === "register"
                ? "Creating account…"
                : "Signing in…"
              : mode === "register"
                ? "Create account"
                : "Sign in with email"}
          </button>
          {mode === "register" && (
            <p className="disclaimer" style={{ marginTop: 10 }}>
              We’ll email you a short summary of what ImmiAssist does after you register.
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
