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

function EyeIcon({ open }) {
  if (open) {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"
          stroke="currentColor"
          strokeWidth="1.75"
        />
        <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.75" />
      </svg>
    );
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 3l18 18M10.5 10.7a3 3 0 0 0 4.2 4.2M9.9 5.1A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7a18.3 18.3 0 0 1-4.2 4.8M6.1 6.2A18.5 18.5 0 0 0 2 12s3.5 7 10 7c1.1 0 2.1-.2 3.1-.5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PasswordField({ value, onChange, placeholder, autoComplete, style }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="password-field" style={style}>
      <input
        className="field"
        type={visible ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required
        minLength={8}
      />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Hide password" : "Show password"}
        title={visible ? "Hide password" : "Show password"}
      >
        <EyeIcon open={visible} />
      </button>
    </div>
  );
}

function JourneyVisual() {
  return (
    <aside className="login-visual" aria-hidden="true">
      <div className="login-visual-scene">
        <div className="orbit orbit-a" />
        <div className="orbit orbit-b" />
        <div className="passport-card">
          <div className="passport-stamp">IA</div>
          <p>Status: Preparing</p>
          <h3>Your next step, clarified.</h3>
          <ul>
            <li>Visa pathways</li>
            <li>Document checklists</li>
            <li>Timeline estimates</li>
          </ul>
        </div>
        <div className="float-chip chip-a">I-485</div>
        <div className="float-chip chip-b">H-1B</div>
        <div className="float-chip chip-c">RFE</div>
      </div>
    </aside>
  );
}

export default function LoginPage() {
  const { user, loading, setUser, refresh } = useAuth();
  const router = useRouter();
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showEmail, setShowEmail] = useState(false);
  const [mode, setMode] = useState("login");
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
          width: 360,
          text: "continue_with",
          shape: "pill",
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
          setNotice("Account created. Welcome summary prepared for your email.");
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
      <div className="login-landing">
        <div className="login-panel">
          <p style={{ color: "var(--muted)" }}>Checking session…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-landing">
      <div className="login-panel">
        <div className="brand-mark brand-mark-lg">
          <div className="mark">IA</div>
          <div>
            <h1>ImmiAssist</h1>
            <p>Immigration guidance</p>
          </div>
        </div>

        <h2 className="login-hero-title">Ask clearly. File calmly.</h2>
        <p className="login-hero-sub">
          Grounded answers on visas, documents, timelines, and RFEs — so you can take the next step
          with less guesswork.
        </p>

        {error && <div className="error-banner">{error}</div>}
        {notice && (
          <div
            className="error-banner"
            style={{ background: "rgba(15, 118, 110, 0.12)", color: "var(--ink)" }}
          >
            {notice}
          </div>
        )}

        <div className="login-cta-stack">
          {config?.google_client_id ? (
            <div ref={googleBtn} className="google-btn-slot" />
          ) : (
            <p className="disclaimer">Google sign-in is not configured yet.</p>
          )}

          {!showEmail ? (
            <button
              type="button"
              className="btn btn-ghost email-cta"
              onClick={() => setShowEmail(true)}
            >
              Sign in with email
            </button>
          ) : (
            <div className="email-auth-block">
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
                  Join now
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
                <PasswordField
                  style={{ marginBottom: mode === "register" ? 8 : 10 }}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                />
                {mode === "register" && (
                  <PasswordField
                    style={{ marginBottom: 10 }}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm password"
                    autoComplete="new-password"
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
              </form>
            </div>
          )}
        </div>

        <p className="login-legal">
          By continuing, you agree this tool provides informational guidance only — not legal advice.
        </p>

        {!showEmail && (
          <p className="login-join">
            New to ImmiAssist?{" "}
            <button
              type="button"
              className="text-link"
              onClick={() => {
                setShowEmail(true);
                setMode("register");
              }}
            >
              Join now
            </button>
          </p>
        )}
      </div>

      <JourneyVisual />
    </div>
  );
}
