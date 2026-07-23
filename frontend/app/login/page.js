"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getAuthConfig, loginDev, loginWithGoogle } from "../../lib/api";
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
  const [busy, setBusy] = useState(false);
  const [devEmail, setDevEmail] = useState("demo@immiassist.local");
  const [devName, setDevName] = useState("Demo User");
  const googleBtn = useRef(null);

  useEffect(() => {
    getAuthConfig()
      .then(setConfig)
      .catch(() => setConfig({ google_client_id: null, auth_dev_mode: true }));
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

  const handleDevLogin = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await loginDev(devEmail, devName);
      setUser(data.user);
      await refresh();
      router.replace("/");
    } catch (err) {
      setError(err.message || "Dev login failed");
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
          Continue with Google to access chat history, settings, and your saved provider keys.
        </p>

        {error && <div className="error-banner">{error}</div>}

        {config?.google_client_id ? (
          <div ref={googleBtn} style={{ display: "flex", justifyContent: "center", minHeight: 44 }} />
        ) : (
          <p className="disclaimer">
            Google Client ID is not configured. Set <code>GOOGLE_CLIENT_ID</code> on the backend,
            or enable <code>AUTH_DEV_MODE=true</code> for local testing.
          </p>
        )}

        {config?.auth_dev_mode && (
          <form onSubmit={handleDevLogin} style={{ marginTop: 18 }}>
            <p className="disclaimer" style={{ marginBottom: 10 }}>
              Development sign-in (AUTH_DEV_MODE)
            </p>
            <input
              className="field"
              style={{ marginBottom: 8 }}
              value={devName}
              onChange={(e) => setDevName(e.target.value)}
              placeholder="Name"
            />
            <input
              className="field"
              type="email"
              style={{ marginBottom: 10 }}
              value={devEmail}
              onChange={(e) => setDevEmail(e.target.value)}
              placeholder="Email"
              required
            />
            <button className="btn btn-primary" style={{ width: "100%" }} disabled={busy}>
              {busy ? "Signing in…" : "Continue with email (dev)"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
