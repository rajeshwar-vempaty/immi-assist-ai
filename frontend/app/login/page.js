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

function waitForGoogle(timeoutMs = 10000) {
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
    }, 50);
  });
}

function GoogleGIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#FFC107"
        d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z"
      />
      <path
        fill="#FF3D00"
        d="M6.3 14.7l6.6 4.8C14.7 16 19 12 24 12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.3 4 24 4 16.1 4 9.2 8.5 6.3 14.7z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.3 35.4 26.8 36 24 36c-5.3 0-9.7-3.3-11.3-8l-6.5 5C9.1 39.5 16 44 24 44z"
      />
      <path
        fill="#1976D2"
        d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4.1 5.5l.1.1 6.2 5.2C39.2 37.1 44 32 44 24c0-1.2-.1-2.3-.4-3.5z"
      />
    </svg>
  );
}

function GoogleSignInButton({ clientId, disabled, onCredential, onError }) {
  const hostRef = useRef(null);
  const [gisReady, setGisReady] = useState(false);
  const [initError, setInitError] = useState(null);
  const onCredentialRef = useRef(onCredential);
  const onErrorRef = useRef(onError);
  const initGen = useRef(0);

  useEffect(() => {
    onCredentialRef.current = onCredential;
    onErrorRef.current = onError;
  }, [onCredential, onError]);

  useEffect(() => {
    if (!clientId) return undefined;

    const host = hostRef.current;
    if (!host) return undefined;

    const gen = ++initGen.current;
    let cancelled = false;
    let ro = null;

    const render = async () => {
      try {
        await waitForGoogle();
        if (cancelled || gen !== initGen.current || !hostRef.current) return;

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => onCredentialRef.current?.(response),
          cancel_on_tap_outside: true,
        });

        const el = hostRef.current;
        const width = Math.max(280, Math.round(el.getBoundingClientRect().width) || 360);
        el.innerHTML = "";
        window.google.accounts.id.renderButton(el, {
          theme: "outline",
          size: "large",
          width,
          text: "continue_with",
          shape: "rectangular",
          logo_alignment: "left",
        });

        if (!cancelled && gen === initGen.current) {
          setGisReady(true);
          setInitError(null);
        }
      } catch (err) {
        if (!cancelled && gen === initGen.current) {
          setGisReady(false);
          const message = err.message || "Could not initialize Google sign-in";
          setInitError(message);
          onErrorRef.current?.(message);
        }
      }
    };

    const start = () => {
      const el = hostRef.current;
      if (!el) return;
      if (el.getBoundingClientRect().width < 40) {
        ro = new ResizeObserver(() => {
          if (hostRef.current && hostRef.current.getBoundingClientRect().width >= 40) {
            ro?.disconnect();
            ro = null;
            render();
          }
        });
        ro.observe(el);
        return;
      }
      render();
    };

    start();

    return () => {
      cancelled = true;
      ro?.disconnect();
    };
  }, [clientId]);

  const handleFallbackClick = () => {
    if (disabled) return;
    if (gisReady) return; // GIS overlay should receive the click
    onErrorRef.current?.(initError || "Google sign-in is still loading. Try again in a moment.");
  };

  return (
    <div className={`google-btn-wrap ${gisReady ? "is-ready" : ""}`}>
      <button
        type="button"
        className="google-btn-fallback"
        onClick={handleFallbackClick}
        disabled={disabled}
        tabIndex={gisReady ? -1 : 0}
      >
        <GoogleGIcon />
        <span>{disabled ? "Please wait…" : "Continue with Google"}</span>
      </button>
      <div ref={hostRef} className="google-btn-slot" aria-hidden={!gisReady} />
    </div>
  );
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

const LOGIN_HERO_COPY = [
  {
    id: "ask-clearly",
    title: "Ask clearly. File calmly.",
    subtitle:
      "Grounded answers on visas, documents, timelines, and RFEs — so you can take the next step with less guesswork.",
  },
  {
    id: "next-step",
    title: "One clear next step.",
    subtitle:
      "Cut through immigration noise with practical guidance on forms, evidence, and what usually comes next.",
  },
  {
    id: "less-guesswork",
    title: "Less guesswork. More clarity.",
    subtitle:
      "Understand pathways, checklists, and timelines in plain language — then move forward with confidence.",
  },
  {
    id: "ready-to-file",
    title: "Know before you file.",
    subtitle:
      "Get oriented on visa options, document readiness, and RFE risks before the paperwork piles up.",
  },
  {
    id: "steady-guidance",
    title: "Steady guidance for big moves.",
    subtitle:
      "From first questions to filing prep — clear answers when the stakes feel high and the forms feel endless.",
  },
  {
    id: "path-forward",
    title: "Find your path forward.",
    subtitle:
      "Explore eligibility signals, wait-time ranges, and document checklists without drowning in jargon.",
  },
];

function pickPerVisit(items, { lastKey, onceKey, forcedId } = {}) {
  if (!items?.length) return null;
  if (forcedId) {
    return items.find((item) => item.id === forcedId) || items[0];
  }
  if (typeof window === "undefined") return items[0];

  const loadId = String(performance.timeOrigin);
  try {
    const raw = sessionStorage.getItem(onceKey);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.loadId === loadId && parsed?.id) {
        const found = items.find((item) => item.id === parsed.id);
        if (found) return found;
      }
    }

    const lastId = sessionStorage.getItem(lastKey);
    const pool = items.filter((item) => item.id !== lastId);
    const choices = pool.length ? pool : items;
    const next = choices[Math.floor(Math.random() * choices.length)];
    sessionStorage.setItem(onceKey, JSON.stringify({ id: next.id, loadId }));
    sessionStorage.setItem(lastKey, next.id);
    return next;
  } catch {
    return items[Math.floor(Math.random() * items.length)];
  }
}

function readClientPick(items, keys) {
  if (typeof window === "undefined") return items[0];
  const params = new URLSearchParams(window.location.search);
  const forcedId = params.get(keys.param);
  return (
    pickPerVisit(items, {
      lastKey: keys.lastKey,
      onceKey: keys.onceKey,
      forcedId,
    }) || items[0]
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
        <div className="passport-stamp">Be</div>
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
        <div className="passport-stamp">Be</div>
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
          <div className="passport-stamp">Be</div>
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
        <div className="passport-stamp">Be</div>
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
        <div className="passport-stamp">Be</div>
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
  // Stable default for SSR + first client paint; rotate after mount to avoid hydration mismatch.
  const [visual, setVisual] = useState(JOURNEY_VISUALS[0]);
  const [animated, setAnimated] = useState(false);

  useEffect(() => {
    setVisual(
      readClientPick(JOURNEY_VISUALS, {
        param: "visual",
        lastKey: "immi_login_visual_id",
        onceKey: "immi_login_visual_once",
      })
    );
    const timer = window.setTimeout(() => setAnimated(true), 80);
    return () => window.clearTimeout(timer);
  }, []);

  const Renderer = JOURNEY_RENDERERS[visual.id] || JourneyVisualOrbit;

  return (
    <aside
      className={`login-visual login-visual-${visual.id} ${animated ? "is-animated" : ""}`}
      aria-hidden="true"
    >
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
  const [heroCopy, setHeroCopy] = useState(LOGIN_HERO_COPY[0]);

  useEffect(() => {
    getAuthConfig()
      .then(setConfig)
      .catch(() => setConfig({ google_client_id: null, password_auth_enabled: true }));
  }, []);

  useEffect(() => {
    setHeroCopy(
      readClientPick(LOGIN_HERO_COPY, {
        param: "hero",
        lastKey: "immi_login_hero_id",
        onceKey: "immi_login_hero_once",
      })
    );
  }, []);

  useEffect(() => {
    if (!loading && user) router.replace("/");
  }, [user, loading, router]);

  const handleGoogleCredential = async (response) => {
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
  };

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

  if (loading && user) {
    return (
      <div className="login-landing">
        <div className="login-panel">
          <p style={{ color: "var(--muted)" }}>Taking you in…</p>
        </div>
      </div>
    );
  }

  // Show the full login chrome immediately (do not wait on session check),
  // so Google + visual mount once and stay stable across refresh.
  const title = showEmail
    ? mode === "register"
      ? "Create your account"
      : "Welcome back"
    : heroCopy.title;

  const subtitle = showEmail
    ? mode === "register"
      ? "Join with email to keep chat history and API keys private to your account."
      : "Sign in with email, or keep using Google above."
    : heroCopy.subtitle;

  return (
    <div className={`login-landing ${showEmail ? "is-email-open" : ""}`}>
      <div className="login-panel">
        <header className="login-panel-header">
          <div className="brand-mark brand-mark-lg">
            <div className="mark">Be</div>
            <div>
              <h1>Beacon</h1>
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
              <GoogleSignInButton
                clientId={config.google_client_id}
                disabled={busy || loading}
                onCredential={handleGoogleCredential}
                onError={setError}
              />
            ) : config ? (
              <p className="disclaimer">Google sign-in is not configured yet.</p>
            ) : (
              <div className="google-btn-wrap">
                <div className="google-btn-fallback" aria-hidden="true">
                  <GoogleGIcon />
                  <span>Continue with Google</span>
                </div>
              </div>
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
                : "New to Beacon?"
              : "New to Beacon?"}{" "}
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
