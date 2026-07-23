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

  if (loading || !user) {
    return (
      <div className="content">
        <p style={{ color: "var(--muted)" }}>Loading…</p>
      </div>
    );
  }

  if (!prefs) {
    return (
      <div className="content settings-page">
        {error && <div className="error-banner">{error}</div>}
        <p style={{ color: "var(--muted)" }}>{busy ? "Loading settings…" : "Preparing settings…"}</p>
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

  return (
    <div className="settings-shell">
      <header className="topbar">
        <Link href="/" className="btn btn-ghost">
          ← Back to chat
        </Link>
        <div className="user-chip">
          {user.picture ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.picture} alt="" className="avatar-img" />
          ) : (
            <span className="avatar">{(user.name || user.email || "U").trim().slice(0, 2).toUpperCase()}</span>
          )}
          <span>{user.name || user.email}</span>
        </div>
        <button className="btn btn-ghost" onClick={signOut}>
          Sign out
        </button>
      </header>

      <main className="content">
        <h2 className="section-title">Profile & settings</h2>
        <p className="section-sub">
          Manage your account defaults and encrypted provider API keys.
        </p>

        {error && <div className="error-banner">{error}</div>}

        <section className="settings-card">
          <h3>Your profile</h3>
          <div className="profile-row">
            {user.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={user.picture} alt="" className="avatar-img lg" />
            ) : (
              <span className="avatar lg">
                {(user.name || user.email || "U").trim().slice(0, 2).toUpperCase()}
              </span>
            )}
            <div>
              <strong>{user.name || "User"}</strong>
              <div style={{ color: "var(--muted)" }}>{user.email}</div>
            </div>
          </div>
        </section>

        <section className="settings-card">
          <h3>Default model</h3>
          <div className="panel-stack">
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
              <option value="">Select provider</option>
              {(prefs?.catalog || [])
                .filter((c) => c.configured)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
            </select>
            <select
              className="select"
              value={prefs?.default_model || ""}
              onChange={(e) => onPrefs({ default_model: e.target.value || null })}
              disabled={!prefs?.default_provider}
            >
              <option value="">Select model</option>
              {(
                prefs?.catalog?.find((c) => c.id === prefs?.default_provider)?.models || []
              ).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={!!prefs?.allow_fallback}
                onChange={(e) => onPrefs({ allow_fallback: e.target.checked })}
              />
              Allow fallback to another configured provider on failure
            </label>
          </div>
        </section>

        <section className="settings-card">
          <h3>Provider API keys</h3>
          <p className="disclaimer">
            Keys are encrypted on the server. The full key is never returned to the browser after
            saving.
          </p>
          <div className="provider-grid">
            {(prefs?.catalog || []).map((provider) => {
              const saved = byProvider[provider.id];
              return (
                <div key={provider.id} className="provider-card">
                  <div className="provider-head">
                    <strong>{provider.label}</strong>
                    <span className={`pill ${saved ? (saved.is_valid ? "ok" : "warn") : "muted"}`}>
                      {saved
                        ? saved.is_valid
                          ? `Configured ${saved.masked_key}`
                          : `Saved ${saved.masked_key} (invalid)`
                        : "Not configured"}
                    </span>
                  </div>
                  <input
                    className="field"
                    type="password"
                    placeholder={saved ? "Enter new key to replace" : "Paste API key"}
                    value={draftKeys[provider.id] || ""}
                    onChange={(e) =>
                      setDraftKeys((d) => ({ ...d, [provider.id]: e.target.value }))
                    }
                    autoComplete="off"
                  />
                  <div className="provider-actions">
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
                  {status[provider.id] && (
                    <p className="disclaimer" style={{ marginTop: 8 }}>
                      {status[provider.id]}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
