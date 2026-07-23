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

function PasswordField({ value, onChange, placeholder, autoComplete }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="password-field">
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

const JOURNEY_VISUALS = [
  {
    id: "orbit",
    status: "Status: Preparing",
    title: "Your next step, clarified.",
    items: ["Visa pathways", "Document checklists", "Timeline estimates"],
    chips: ["I-485", "H-1B", "RFE"],
  },
  {
    id: "timeline",
    status: "Case progress",
    title: "From question to filing plan.",
    items: ["Understand your path", "Gather the right docs", "Track each milestone"],
    chips: ["N-400", "I-130", "EAD"],
  },
  {
    id: "dossier",
    status: "Document room",
    title: "Know what to file — and why.",
    items: ["Evidence checklist", "Form readiness", "RFE risk notes"],
    chips: ["I-765", "DS-160", "I-94"],
  },
  {
    id: "route",
    status: "Pathway map",
    title: "See the route before you move.",
    items: ["Eligibility signals", "Wait-time ranges", "Next action only"],
    chips: ["EB-2", "L-1A", "OPT"],
  },
  {
    id: "horizon",
    status: "Calm guidance",
    title: "Less guesswork. More clarity.",
    items: ["Plain-language answers", "Deadline awareness", "Grounded next steps"],
    chips: ["F-1", "H-4", "CR-1"],
  },
];

function JourneyVisualOrbit({ visual }) {
  return (
    <div className="login-visual-scene visual-orbit">
      <div className="orbit orbit-a" />
      <div className="orbit orbit-b" />
      <div className="passport-card">
        <div className="passport-stamp">IA</div>
        <p>{visual.status}</p>
        <h3>{visual.title}</h3>
        <ul>
          {visual.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      {visual.chips.map((chip, i) => (
        <div key={chip} className={`float-chip chip-${String.fromCharCode(97 + i)}`}>
          {chip}
        </div>
      ))}
    </div>
  );
}

function JourneyVisualTimeline({ visual }) {
  return (
    <div className="login-visual-scene visual-timeline">
      <div className="timeline-rail" />
      <div className="timeline-panel">
        <div className="passport-stamp">IA</div>
        <p>{visual.status}</p>
        <h3>{visual.title}</h3>
        <ol className="timeline-steps">
          {visual.items.map((item, i) => (
            <li key={item}>
              <span className="step-dot">{i + 1}</span>
              <span>{item}</span>
            </li>
          ))}
        </ol>
      </div>
      {visual.chips.map((chip, i) => (
        <div key={chip} className={`float-chip chip-t${i + 1}`}>
          {chip}
        </div>
      ))}
    </div>
  );
}

function JourneyVisualDossier({ visual }) {
  return (
    <div className="login-visual-scene visual-dossier">
      <div className="dossier-stack">
        <div className="dossier-sheet sheet-back" />
        <div className="dossier-sheet sheet-mid" />
        <div className="dossier-sheet sheet-front">
          <div className="passport-stamp">IA</div>
          <p>{visual.status}</p>
          <h3>{visual.title}</h3>
          <ul>
            {visual.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
      {visual.chips.map((chip, i) => (
        <div key={chip} className={`float-chip chip-d${i + 1}`}>
          {chip}
        </div>
      ))}
    </div>
  );
}

function JourneyVisualRoute({ visual }) {
  return (
    <div className="login-visual-scene visual-route">
      <svg className="route-path" viewBox="0 0 400 420" fill="none" aria-hidden="true">
        <path
          className="route-line"
          d="M48 340 C 90 250, 120 220, 170 200 S 280 150, 320 80"
        />
        <circle className="route-node route-node-start" cx="48" cy="340" r="7" />
        <circle className="route-node route-node-mid" cx="170" cy="200" r="7" />
        <circle className="route-node route-node-end" cx="320" cy="80" r="7" />
      </svg>
      <div className="route-card">
        <div className="passport-stamp">IA</div>
        <p>{visual.status}</p>
        <h3>{visual.title}</h3>
        <ul>
          {visual.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      {visual.chips.map((chip, i) => (
        <div key={chip} className={`float-chip chip-r${i + 1}`}>
          {chip}
        </div>
      ))}
    </div>
  );
}

function JourneyVisualHorizon({ visual }) {
  return (
    <div className="login-visual-scene visual-horizon">
      <div className="horizon-glow" />
      <div className="horizon-line" />
      <div className="horizon-card">
        <div className="passport-stamp">IA</div>
        <p>{visual.status}</p>
        <h3>{visual.title}</h3>
        <ul>
          {visual.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      {visual.chips.map((chip, i) => (
        <div key={chip} className={`float-chip chip-h${i + 1}`}>
          {chip}
        </div>
      ))}
    </div>
  );
}

const JOURNEY_RENDERERS = {
  orbit: JourneyVisualOrbit,
  timeline: JourneyVisualTimeline,
  dossier: JourneyVisualDossier,
  route: JourneyVisualRoute,
  horizon: JourneyVisualHorizon,
};

function JourneyVisual() {
  const [visual, setVisual] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const forced = params.get("visual");
    if (forced) {
      const match = JOURNEY_VISUALS.find((v) => v.id === forced);
      if (match) {
        setVisual(match);
        return;
      }
    }

    const lastKey = "immi_login_visual_id";
    const onceKey = "immi_login_visual_once";
    const loadId = String(performance.timeOrigin);

    try {
      const raw = sessionStorage.getItem(onceKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed?.loadId === loadId && parsed?.id) {
          const found = JOURNEY_VISUALS.find((v) => v.id === parsed.id);
          if (found) {
            setVisual(found);
            return;
          }
        }
      }

      const lastId = sessionStorage.getItem(lastKey);
      const pool = JOURNEY_VISUALS.filter((v) => v.id !== lastId);
      const choices = pool.length ? pool : JOURNEY_VISUALS;
      const next = choices[Math.floor(Math.random() * choices.length)];
      sessionStorage.setItem(onceKey, JSON.stringify({ id: next.id, loadId }));
      sessionStorage.setItem(lastKey, next.id);
      setVisual(next);
    } catch {
      setVisual(JOURNEY_VISUALS[Math.floor(Math.random() * JOURNEY_VISUALS.length)]);
    }
  }, []);

  if (!visual) {
    return <aside className="login-visual" aria-hidden="true" />;
  }

  const Renderer = JOURNEY_RENDERERS[visual.id] || JourneyVisualOrbit;

  return (
    <aside className={`login-visual login-visual-${visual.id}`} aria-hidden="true">
      <Renderer visual={visual} />
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

  const openEmail = (nextMode) => {
    setShowEmail(true);
    setMode(nextMode);
    setError(null);
  };

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

  const title = showEmail
    ? mode === "register"
      ? "Create your account"
      : "Welcome back"
    : "Ask clearly. File calmly.";

  const subtitle = showEmail
    ? mode === "register"
      ? "Join with email to keep chat history and API keys private to your account."
      : "Sign in with email, or keep using Google above."
    : "Grounded answers on visas, documents, timelines, and RFEs — so you can take the next step with less guesswork.";

  return (
    <div className={`login-landing ${showEmail ? "is-email-open" : ""}`}>
      <div className="login-panel">
        <header className="login-panel-header">
          <div className="brand-mark brand-mark-lg">
            <div className="mark">IA</div>
            <div>
              <h1>ImmiAssist</h1>
              <p>Immigration guidance</p>
            </div>
          </div>
        </header>

        <div className="login-panel-main">
          <div className="login-copy">
            <h2 className="login-hero-title">{title}</h2>
            <p className="login-hero-sub">{subtitle}</p>
          </div>

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

            <div className={`email-auth-slot ${showEmail ? "open" : ""}`}>
              {!showEmail ? (
                <button
                  type="button"
                  className="btn btn-ghost email-cta"
                  onClick={() => openEmail("login")}
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

                  <form onSubmit={handleSubmit} className="email-auth-form">
                    <div
                      className={`register-extra ${mode === "register" ? "show" : ""}`}
                      aria-hidden={mode !== "register"}
                    >
                      <input
                        className="field"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Username"
                        autoComplete="username"
                        required={mode === "register"}
                        minLength={2}
                        tabIndex={mode === "register" ? 0 : -1}
                      />
                    </div>

                    <input
                      className="field"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Email"
                      autoComplete="email"
                      required
                    />
                    <PasswordField
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Password"
                      autoComplete={mode === "register" ? "new-password" : "current-password"}
                    />

                    <div
                      className={`register-extra ${mode === "register" ? "show" : ""}`}
                      aria-hidden={mode !== "register"}
                    >
                      <PasswordField
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Confirm password"
                        autoComplete="new-password"
                      />
                    </div>

                    <button className="btn btn-primary" style={{ width: "100%" }} disabled={busy}>
                      {busy
                        ? mode === "register"
                          ? "Creating account…"
                          : "Signing in…"
                        : mode === "register"
                          ? "Create account"
                          : "Sign in with email"}
                    </button>

                    <button
                      type="button"
                      className="text-link back-link"
                      onClick={() => {
                        setShowEmail(false);
                        setError(null);
                      }}
                    >
                      ← Back to options
                    </button>
                  </form>
                </div>
              )}
            </div>
          </div>

          <div className="login-main-spacer" aria-hidden="true" />
        </div>

        <footer className="login-panel-footer">
          <p className="login-legal">
            By continuing, you agree this tool provides informational guidance only — not legal advice.
          </p>
          <p className="login-join">
            {showEmail
              ? mode === "register"
                ? "Already have an account?"
                : "New to ImmiAssist?"
              : "New to ImmiAssist?"}{" "}
            <button
              type="button"
              className="text-link"
              onClick={() => {
                if (!showEmail) openEmail("register");
                else setMode(mode === "register" ? "login" : "register");
              }}
            >
              {showEmail
                ? mode === "register"
                  ? "Sign in"
                  : "Join now"
                : "Join now"}
            </button>
          </p>
        </footer>
      </div>

      <JourneyVisual />
    </div>
  );
}
