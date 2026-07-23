"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "../../lib/auth";
import {
  deleteCredential,
  getSettingsPreferences,
  listCredentials,
  saveCredential,
  testCredential,
  updateSettingsPreferences,
} from "../../lib/api";

function initialsFor(user) {
  const raw = (user?.name || user?.email || "U").trim();
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return raw.slice(0, 2).toUpperCase();
}

export default function SettingsPage() {
  const { user, loading, signOut } = useAuth();
  const [prefs, setPrefs] = useState(null);
  const [credentials, setCredentials] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setBusy(true);
    setError(null);
    try {
      const [p, c] = await Promise.all([getSettingsPreferences(), listCredentials()]);
      setPrefs(p);
      setCredentials(c.credentials || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (user) load();
  }, [user]);

  const byProvider = useMemo(() => {
    const map = {};
    credentials.forEach((c) => {
      map[c.provider] = c;
    });
    return map;
  }, [credentials]);

  const configuredProviders = useMemo(
    () => (prefs?.catalog || []).filter((c) => c.configured),
    [prefs]
  );

  const modelsForDefault = useMemo(() => {
    return prefs?.catalog?.find((c) => c.id === prefs?.default_provider)?.models || [];
  }, [prefs]);

  if (loading || !user) {
    return (
      <div className="settings-shell">
        <main className="settings-main">
          <p style={{ color: "var(--muted)" }}>Loading…</p>
        </main>
      </div>
    );
  }

  if (!prefs) {
    return (
      <div className="settings-shell">
        <main className="settings-main">
          {error && <div className="error-banner">{error}</div>}
          <p style={{ color: "var(--muted)" }}>{busy ? "Loading settings…" : "Preparing settings…"}</p>
        </main>
      </div>
    );
  }

  const onPrefs = async (patch) => {
    setBusy(true);
    try {
      const next = await updateSettingsPreferences(patch);
      setPrefs(next);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const initials = initialsFor(user);

  return (
    <div className="settings-shell">
      <header className="settings-topbar">
        <Link href="/" className="btn btn-ghost">
          ← Chat
        </Link>
        <button className="btn btn-ghost" onClick={signOut}>
          Sign out
        </button>
      </header>

      <main className="settings-main">
        <header className="settings-intro">
          <div className="settings-intro-text">
            <h1>Settings</h1>
            <p>Defaults for chat, and encrypted provider keys.</p>
          </div>
          <div className="settings-identity">
            {user.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={user.picture} alt="" className="avatar-img" />
            ) : (
              <span className="avatar">{initials}</span>
            )}
            <div>
              <strong>{user.name || "User"}</strong>
              <span>{user.email}</span>
            </div>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button type="button" className="banner-dismiss" onClick={() => setError(null)} aria-label="Dismiss">
              ×
            </button>
          </div>
        )}

        <section className="settings-block">
          <div className="settings-block-head">
            <h2>Chat defaults</h2>
            {configuredProviders.length === 0 && (
              <span className="settings-note">Add a key below to unlock providers.</span>
            )}
          </div>

          <div className="settings-inline-fields">
            <label className="settings-field">
              <span>Provider</span>
              <select
                className="select"
                value={prefs?.default_provider || ""}
                onChange={(e) =>
                  onPrefs({
                    default_provider: e.target.value || null,
                    default_model:
                      prefs?.catalog?.find((c) => c.id === e.target.value)?.models?.[0]?.id || null,
                  })
                }
              >
                <option value="">Select…</option>
                {configuredProviders.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="settings-field">
              <span>Model</span>
              <select
                className="select"
                value={prefs?.default_model || ""}
                onChange={(e) => onPrefs({ default_model: e.target.value || null })}
                disabled={!prefs?.default_provider}
              >
                <option value="">Select…</option>
                {modelsForDefault.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="settings-check">
            <input
              type="checkbox"
              checked={!!prefs?.allow_fallback}
              onChange={(e) => onPrefs({ allow_fallback: e.target.checked })}
            />
            <span>Fall back to another configured provider if the default fails</span>
          </label>
        </section>

        <section className="settings-block">
          <div className="settings-block-head">
            <h2>API keys</h2>
            <span className="settings-note">Encrypted on the server. Full keys never leave storage.</span>
          </div>

          <ApiKeyWizard
            catalog={prefs?.catalog || []}
            byProvider={byProvider}
            busy={busy}
            onReload={load}
            setBusy={setBusy}
            setError={setError}
          />
        </section>
      </main>
    </div>
  );
}

function ApiKeyWizard({ catalog, byProvider, busy, onReload, setBusy, setError }) {
  const firstConfigured = catalog.find((p) => byProvider[p.id])?.id || catalog[0]?.id || "";
  const [provider, setProvider] = useState(firstConfigured);
  const [apiKey, setApiKey] = useState("");
  const [replacing, setReplacing] = useState(false);
  const [phase, setPhase] = useState("idle"); // idle | saving | testing | done | error
  const [failedAt, setFailedAt] = useState(0); // 0 = save, 1 = test
  const [localMsg, setLocalMsg] = useState("");

  useEffect(() => {
    if (!provider && catalog[0]?.id) setProvider(catalog[0].id);
  }, [catalog, provider]);

  const selected = catalog.find((p) => p.id === provider) || catalog[0];
  const saved = selected ? byProvider[selected.id] : null;
  const running = phase === "saving" || phase === "testing";
  const showProgress = running || phase === "done" || phase === "error";

  const steps = [
    { id: "save", label: "Save" },
    { id: "test", label: "Test" },
    { id: "auth", label: "Ready" },
  ];

  function progressWidth() {
    if (phase === "done") return "100%";
    if (phase === "saving") return "33%";
    if (phase === "testing") return "66%";
    if (phase === "error") return failedAt === 0 ? "33%" : "66%";
    return "0%";
  }

  function stepState(idx) {
    if (phase === "done") return "done";
    if (phase === "saving") return idx === 0 ? "active" : "todo";
    if (phase === "testing") {
      if (idx === 0) return "done";
      if (idx === 1) return "active";
      return "todo";
    }
    if (phase === "error") {
      if (idx < failedAt) return "done";
      if (idx === failedAt) return "error";
      return "todo";
    }
    return "todo";
  }

  function selectProvider(id) {
    if (running || busy) return;
    setProvider(id);
    setApiKey("");
    setReplacing(false);
    setPhase("idle");
    setFailedAt(0);
    setLocalMsg("");
  }

  async function runAuthenticate() {
    const key = apiKey.trim();
    if (!key) {
      setLocalMsg("Paste an API key first.");
      setPhase("error");
      return;
    }
    setBusy(true);
    setError(null);
    setLocalMsg("");
    setFailedAt(0);
    setPhase("saving");
    let at = 0;
    try {
      await saveCredential(provider, key);
      at = 1;
      setPhase("testing");
      const result = await testCredential(provider);
      if (!result.is_valid) {
        setFailedAt(1);
        setPhase("error");
        setLocalMsg("Saved, but authentication failed. Check the key and try again.");
        await onReload();
        return;
      }
      setPhase("done");
      setApiKey("");
      setReplacing(false);
      setLocalMsg("Key saved and authenticated.");
      await onReload();
    } catch (err) {
      setFailedAt(at);
      setPhase("error");
      setLocalMsg(err.message || "Could not save or authenticate this key.");
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runTestOnly() {
    setBusy(true);
    setError(null);
    setLocalMsg("");
    setFailedAt(1);
    setPhase("testing");
    try {
      const result = await testCredential(provider);
      if (!result.is_valid) {
        setPhase("error");
        setLocalMsg("Authentication failed. Replace the key and try again.");
        return;
      }
      setPhase("done");
      setLocalMsg("Key authenticated successfully.");
    } catch (err) {
      setPhase("error");
      setLocalMsg(err.message || "Test failed");
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runRemove() {
    if (!confirm(`Remove saved ${selected?.label || provider} API key?`)) return;
    setBusy(true);
    setError(null);
    setLocalMsg("");
    try {
      await deleteCredential(provider);
      setReplacing(false);
      setApiKey("");
      setPhase("idle");
      setLocalMsg("");
      await onReload();
    } catch (err) {
      setPhase("error");
      setLocalMsg(err.message || "Remove failed");
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!catalog.length) {
    return <p className="muted">No providers available.</p>;
  }

  return (
    <div className="api-wizard">
      <div className="api-wizard-providers" role="listbox" aria-label="Choose a provider">
        {catalog.map((p) => {
          const hasKey = Boolean(byProvider[p.id]);
          const isSelected = provider === p.id;
          return (
            <button
              key={p.id}
              type="button"
              role="option"
              aria-selected={isSelected}
              className={`api-wizard-provider${isSelected ? " selected" : ""}${hasKey ? " has-key" : ""}`}
              onClick={() => selectProvider(p.id)}
              disabled={running}
            >
              <span className="api-wizard-provider-name">{p.label}</span>
              <span className={`api-wizard-provider-state${hasKey ? " ok" : ""}`}>
                {hasKey ? "Configured" : "Not set"}
              </span>
            </button>
          );
        })}
      </div>

      <div className="api-wizard-panel">
        {saved && !replacing ? (
          <div className="api-wizard-status-row">
            <div>
              <p className="api-wizard-status-label">Current key</p>
              <p className="api-wizard-status-value">
                <span className={`pill ${saved.is_valid ? "ok" : "warn"}`}>
                  {saved.is_valid ? saved.masked_key : `${saved.masked_key} · invalid`}
                </span>
                <span className="api-wizard-status-hint">Encrypted on the server</span>
              </p>
            </div>
            <div className="api-wizard-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setReplacing(true);
                  setPhase("idle");
                  setLocalMsg("");
                  setApiKey("");
                }}
                disabled={busy || running}
              >
                Replace
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={runTestOnly}
                disabled={busy || running}
              >
                Test
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={runRemove}
                disabled={busy || running}
              >
                Remove
              </button>
            </div>
          </div>
        ) : (
          <>
            <label className="settings-field api-wizard-key-field">
              <span>
                {saved
                  ? `Replace ${selected?.label} key`
                  : `Paste ${selected?.label} API key`}
              </span>
              <input
                className="field"
                type="password"
                autoComplete="off"
                placeholder="Paste API key"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  if (phase === "error" || phase === "done") setPhase("idle");
                  setLocalMsg("");
                }}
                disabled={busy || running}
              />
            </label>
            <div className="api-wizard-actions">
              <button
                type="button"
                className="btn btn-primary"
                onClick={runAuthenticate}
                disabled={busy || running || !apiKey.trim()}
              >
                {running ? "Working…" : "Save & authenticate"}
              </button>
              {saved ? (
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => {
                    setReplacing(false);
                    setApiKey("");
                    setPhase("idle");
                    setLocalMsg("");
                  }}
                  disabled={busy || running}
                >
                  Cancel
                </button>
              ) : null}
            </div>
          </>
        )}

        {showProgress ? (
          <div className="api-wizard-progress" aria-live="polite">
            <div className="api-wizard-steps">
              {steps.map((step, idx) => (
                <div key={step.id} className={`api-wizard-step ${stepState(idx)}`}>
                  <span className="api-wizard-step-dot" aria-hidden="true" />
                  <span className="api-wizard-step-label">{step.label}</span>
                </div>
              ))}
            </div>
            <div className="api-wizard-track" aria-hidden="true">
              <div
                className={`api-wizard-track-fill${phase === "error" ? " error" : ""}${phase === "done" ? " done" : ""}`}
                style={{ width: progressWidth() }}
              />
            </div>
            {localMsg ? (
              <p className={`api-wizard-msg${phase === "error" ? " error" : ""}`}>{localMsg}</p>
            ) : running ? (
              <p className="api-wizard-msg">
                {phase === "saving" ? "Saving encrypted key…" : "Testing authentication…"}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
