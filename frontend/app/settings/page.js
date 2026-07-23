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
  const [draftKeys, setDraftKeys] = useState({});
  const [status, setStatus] = useState({});
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

  const onSave = async (provider) => {
    const key = draftKeys[provider];
    if (!key) {
      setStatus((s) => ({ ...s, [provider]: "Enter a key to save." }));
      return;
    }
    setBusy(true);
    try {
      const result = await saveCredential(provider, key);
      setStatus((s) => ({
        ...s,
        [provider]: result.is_valid ? "Saved and validated." : "Saved, but validation failed.",
      }));
      setDraftKeys((d) => ({ ...d, [provider]: "" }));
      await load();
    } catch (err) {
      setStatus((s) => ({ ...s, [provider]: err.message }));
    } finally {
      setBusy(false);
    }
  };

  const onTest = async (provider) => {
    setBusy(true);
    try {
      const key = draftKeys[provider] || null;
      const result = await testCredential(provider, key);
      setStatus((s) => ({
        ...s,
        [provider]: result.is_valid ? "Key is valid." : "Key is invalid.",
      }));
      await load();
    } catch (err) {
      setStatus((s) => ({ ...s, [provider]: err.message }));
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (provider) => {
    if (!confirm(`Remove saved ${provider} API key?`)) return;
    setBusy(true);
    try {
      await deleteCredential(provider);
      setStatus((s) => ({ ...s, [provider]: "Removed." }));
      await load();
    } catch (err) {
      setStatus((s) => ({ ...s, [provider]: err.message }));
    } finally {
      setBusy(false);
    }
  };

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

          <div className="key-list">
            {(prefs?.catalog || []).map((provider) => {
              const saved = byProvider[provider.id];
              return (
                <div key={provider.id} className="key-row">
                  <div className="key-row-meta">
                    <strong>{provider.label}</strong>
                    <span className={`pill ${saved ? (saved.is_valid ? "ok" : "warn") : "muted"}`}>
                      {saved
                        ? saved.is_valid
                          ? saved.masked_key
                          : `${saved.masked_key} · invalid`
                        : "Not set"}
                    </span>
                  </div>
                  <div className="key-row-controls">
                    <input
                      className="field"
                      type="password"
                      placeholder={saved ? "Replace key…" : "Paste API key"}
                      value={draftKeys[provider.id] || ""}
                      onChange={(e) =>
                        setDraftKeys((d) => ({ ...d, [provider.id]: e.target.value }))
                      }
                      autoComplete="off"
                    />
                    <div className="key-row-actions">
                      <button
                        className="btn btn-primary"
                        disabled={busy}
                        onClick={() => onSave(provider.id)}
                      >
                        Save
                      </button>
                      <button
                        className="btn btn-ghost"
                        disabled={busy}
                        onClick={() => onTest(provider.id)}
                      >
                        Test
                      </button>
                      {saved && (
                        <button
                          className="btn btn-ghost"
                          disabled={busy}
                          onClick={() => onDelete(provider.id)}
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  </div>
                  {status[provider.id] ? <p className="key-row-status">{status[provider.id]}</p> : null}
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
