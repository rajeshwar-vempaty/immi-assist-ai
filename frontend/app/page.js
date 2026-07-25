"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { useAuth } from "../lib/auth";
import ChatThinking from "../components/ChatThinking";
import {
  analyzeRFE,
  createChecklist,
  deleteConversation,
  getConversation,
  getSettingsPreferences,
  getUscisCategories,
  getUscisForms,
  getUscisOffices,
  getUscisProcessingTime,
  listConversations,
  sendChatMessage,
  truncateConversation,
} from "../lib/api";

const TABS = [
  { id: "chat", label: "Chat" },
  { id: "checklist", label: "Checklist" },
  { id: "timeline", label: "Timeline" },
  { id: "rfe", label: "RFE" },
];

const QUICK_QUESTIONS = [
  "How do I transfer my H-1B to a new employer?",
  "What documents do I need for I-485 filing?",
  "What is the EB-2 NIW process?",
  "My OPT expires in 60 days — what are my options?",
];

const VISA_TYPES = [
  "H1B", "H4", "L1A", "L1B", "O1", "EB1", "EB2", "EB3", "EB2_NIW",
  "F1", "F1_OPT", "I485", "I130", "I140", "TN", "OTHER",
];

function UscisTimeline() {
  const [forms, setForms] = useState([]);
  const [categories, setCategories] = useState([]);
  const [offices, setOffices] = useState([]);
  const [form, setForm] = useState("");
  const [category, setCategory] = useState("");
  const [office, setOffice] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stepLoading, setStepLoading] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getUscisForms()
      .then((d) => setForms(d.forms || []))
      .catch((e) => setError(e.message));
  }, []);

  const onFormChange = async (id) => {
    setForm(id);
    setCategory("");
    setOffice("");
    setCategories([]);
    setOffices([]);
    setResult(null);
    setError("");
    if (!id) return;
    setStepLoading("categories");
    try {
      const d = await getUscisCategories(id);
      setCategories(d.categories || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setStepLoading("");
    }
  };

  const onCategoryChange = async (id) => {
    setCategory(id);
    setOffice("");
    setOffices([]);
    setResult(null);
    setError("");
    if (!id) return;
    setStepLoading("offices");
    try {
      const d = await getUscisOffices(form, id);
      const list = d.offices || [];
      setOffices(list);
      if (list.length === 1) setOffice(list[0].id);
    } catch (e) {
      setError(e.message);
    } finally {
      setStepLoading("");
    }
  };

  const onGetTime = async () => {
    if (!form || !category || !office || loading) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await getUscisProcessingTime(form, category, office));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const formDesc = forms.find((f) => f.id === form)?.description || "";
  const officeDesc = offices.find((o) => o.id === office)?.description || office;

  return (
    <section className="panel-stack pt-panel">
      <h2 className="section-title">Case processing times</h2>
      <p className="pt-sub">
        The same lookup USCIS offers on{" "}
        <a href="https://egov.uscis.gov/processing-times/" target="_blank" rel="noopener noreferrer">
          egov.uscis.gov/processing-times
        </a>
        : pick a form, category, and office to see how long 80% of cases take.
      </p>

      <label className="pt-field">
        <span>
          Form <em aria-hidden="true">*</em>
        </span>
        <select className="select" value={form} onChange={(e) => onFormChange(e.target.value)}>
          <option value="">Select a form…</option>
          {forms.map((f) => (
            <option key={f.id} value={f.id}>
              {f.id} | {f.description}
            </option>
          ))}
        </select>
      </label>

      <label className="pt-field">
        <span>
          Form Category <em aria-hidden="true">*</em>
        </span>
        <select
          className="select"
          value={category}
          onChange={(e) => onCategoryChange(e.target.value)}
          disabled={!form || stepLoading === "categories"}
        >
          <option value="">
            {stepLoading === "categories" ? "Loading categories…" : "Select a category…"}
          </option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.description}
            </option>
          ))}
        </select>
      </label>

      <label className="pt-field">
        <span>
          Field Office or Service Center <em aria-hidden="true">*</em>
        </span>
        <select
          className="select"
          value={office}
          onChange={(e) => {
            setOffice(e.target.value);
            setResult(null);
          }}
          disabled={!category || stepLoading === "offices"}
        >
          <option value="">
            {stepLoading === "offices" ? "Loading offices…" : "Select an office…"}
          </option>
          {offices.map((o) => (
            <option key={o.id} value={o.id}>
              {o.description}
            </option>
          ))}
        </select>
      </label>

      <div>
        <button
          className="btn btn-primary"
          onClick={onGetTime}
          disabled={!form || !category || !office || loading}
        >
          {loading ? "Checking…" : "Get processing time"}
        </button>
      </div>

      {error ? <p className="pt-error">{error}</p> : null}

      {result && (
        <div className="pt-result">
          <h3 className="pt-result-title">
            Processing time for {formDesc} ({result.form}) at {officeDesc}
          </h3>
          {result.months != null ? (
            <div className="pt-card">
              <div className="pt-card-head">80% of cases are completed within</div>
              <div className="pt-card-value">
                <strong>{result.months}</strong>
                <span>Months</span>
              </div>
            </div>
          ) : (
            <p className="pt-error">
              No published figure for this combination.{" "}
              <a href={result.uscis_url} target="_blank" rel="noopener noreferrer">
                Check directly on USCIS
              </a>
              .
            </p>
          )}
          <p className={`pt-source ${result.source === "live" ? "live" : "cached"}`}>
            {result.source === "live" ? (
              <>
                Live data from{" "}
                <a href={result.uscis_url} target="_blank" rel="noopener noreferrer">
                  egov.uscis.gov
                </a>
                {result.publication_date ? ` — published ${result.publication_date}` : ""}
              </>
            ) : (
              <>
                Cached USCIS figures (as of {result.as_of}) — the live USCIS service could not be
                reached from this server. Verify on{" "}
                <a href={result.uscis_url} target="_blank" rel="noopener noreferrer">
                  egov.uscis.gov
                </a>
                .
              </>
            )}
          </p>
        </div>
      )}
    </section>
  );
}

const markdownComponents = {
  a: ({ node, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer" />
  ),
};

function SourceChips({ sources }) {
  return (
    <div className="sources">
      {sources.slice(0, 4).map((s, j) => {
        const label = typeof s === "string" ? s : s?.label || "Source";
        const url = typeof s === "string" ? "" : s?.url || "";
        return url ? (
          <a
            key={j}
            className="source-chip source-link"
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            title={url}
          >
            {label}
          </a>
        ) : (
          <span key={j} className="source-chip">
            {label}
          </span>
        );
      })}
    </div>
  );
}

function SidebarIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <line x1="9" y1="4" x2="9" y2="20" />
    </svg>
  );
}

function groupHistory(items) {
  const buckets = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Previous 7 days", items: [] },
    { label: "Previous 30 days", items: [] },
    { label: "Older", items: [] },
  ];
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const DAY = 86400000;
  for (const item of items) {
    const t = new Date(item.updated_at).getTime();
    let idx = 4;
    if (Number.isNaN(t)) idx = 4;
    else if (t >= startOfToday) idx = 0;
    else if (t >= startOfToday - DAY) idx = 1;
    else if (t >= startOfToday - 7 * DAY) idx = 2;
    else if (t >= startOfToday - 30 * DAY) idx = 3;
    buckets[idx].items.push(item);
  }
  return buckets.filter((b) => b.items.length > 0);
}

export default function Home() {
  const { user, loading, signOut } = useAuth();
  const [tab, setTab] = useState("chat");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [toolLoading, setToolLoading] = useState(false);
  const [error, setError] = useState(null);
  const [prefs, setPrefs] = useState(null);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [draftReady, setDraftReady] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState(null);
  const [editingIdx, setEditingIdx] = useState(null);
  const [editText, setEditText] = useState("");
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);
  const draftKey = "immi_draft_message";

  const [visaType, setVisaType] = useState("H1B");
  const [checklistDetails, setChecklistDetails] = useState("");
  const [checklistResult, setChecklistResult] = useState(null);
  const [rfeText, setRfeText] = useState("");
  const [rfeResult, setRfeResult] = useState(null);

  const configuredCatalog = useMemo(
    () => (prefs?.catalog || []).filter((c) => c.configured),
    [prefs]
  );

  const modelsForProvider = useMemo(() => {
    const entry = configuredCatalog.find((c) => c.id === provider);
    return entry?.models || [];
  }, [configuredCatalog, provider]);

  useEffect(() => {
    setSidebarCollapsed(localStorage.getItem("immi_sidebar_collapsed") === "1");
  }, []);

  const toggleSidebar = () => {
    setSidebarCollapsed((v) => {
      localStorage.setItem("immi_sidebar_collapsed", v ? "0" : "1");
      return !v;
    });
  };

  useEffect(() => {
    if (!user) return;
    const draft = sessionStorage.getItem(draftKey);
    if (draft) setInput(draft);
    setDraftReady(true);
    (async () => {
      setHistoryLoading(true);
      try {
        const [convData, prefData] = await Promise.all([
          listConversations(),
          getSettingsPreferences(),
        ]);
        setHistory(convData.conversations || []);
        setPrefs(prefData);
        setProvider(prefData.default_provider || "");
        setModel(prefData.default_model || "");
      } catch (err) {
        setError(err.message);
      } finally {
        setHistoryLoading(false);
      }
    })();
  }, [user]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onPointer = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, tab, chatLoading]);

  useEffect(() => {
    if (!draftReady) return;
    sessionStorage.setItem(draftKey, input);
  }, [input, draftReady]);

  if (loading || !user) {
    return (
      <div className="login-shell">
        <div className="login-card">
          <p style={{ color: "var(--muted)" }}>Loading your workspace…</p>
        </div>
      </div>
    );
  }

  const startNewChat = async () => {
    setActiveChatId(null);
    setMessages([]);
    setError(null);
    setChecklistResult(null);
    setTimelineResult(null);
    setRfeResult(null);
    setTab("chat");
    setHistoryOpen(false);
  };

  const openChat = async (id) => {
    setError(null);
    try {
      const detail = await getConversation(id);
      setActiveChatId(detail.id);
      setMessages(
        (detail.messages || []).map((m) => ({
          role: m.role,
          content: m.content,
          meta: { sources: m.sources, model: m.model, provider: m.provider },
        }))
      );
      setTab("chat");
      setHistoryOpen(false);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSignOut = async () => {
    setMessages([]);
    setHistory([]);
    setActiveChatId(null);
    setPrefs(null);
    setError(null);
    await signOut();
  };

  const handleSend = async (messageText = null, baseMessages = null) => {
    const text = messageText || input.trim();
    if (!text || chatLoading) return;
    if (!provider || !model) {
      setError("Select a provider/model in the selector, or add API keys in Settings.");
      return;
    }
    setError(null);
    const base = baseMessages ?? messages;
    const userMessage = { role: "user", content: text };
    const next = [...base, userMessage];
    setMessages(next);
    setInput("");
    sessionStorage.removeItem(draftKey);
    setChatLoading(true);

    try {
      const response = await sendChatMessage({
        message: text,
        chatHistory: base,
        conversationId: activeChatId,
        provider,
        model,
      });
      const assistantMessage = {
        role: "assistant",
        content: response.response,
        meta: {
          intent: response.intent,
          model: response.model_used,
          provider: response.provider,
          sources: response.sources,
        },
      };
      setMessages([...next, assistantMessage]);
      setActiveChatId(response.conversation_id);
      const convData = await listConversations();
      setHistory(convData.conversations || []);
    } catch (err) {
      if (err.status === 401) {
        setError("Session expired. Please sign in again.");
        await handleSignOut();
        return;
      }
      setError(err.message);
    } finally {
      setChatLoading(false);
    }
  };

  const copyMessage = async (content, idx) => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(content);
      } else {
        const ta = document.createElement("textarea");
        ta.value = content;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx((v) => (v === idx ? null : v)), 1600);
    } catch {
      setError("Could not copy to clipboard.");
    }
  };

  const startEdit = (idx) => {
    if (chatLoading) return;
    setEditingIdx(idx);
    setEditText(messages[idx]?.content || "");
  };

  const cancelEdit = () => {
    setEditingIdx(null);
    setEditText("");
  };

  const saveEditAndRerun = async () => {
    const idx = editingIdx;
    const text = editText.trim();
    if (idx === null || !text || chatLoading) return;
    setEditingIdx(null);
    setEditText("");
    const base = messages.slice(0, idx);

    if (activeChatId) {
      try {
        const detail = await getConversation(activeChatId);
        const serverMsg = (detail.messages || [])[idx];
        if (serverMsg && serverMsg.role === "user") {
          await truncateConversation(activeChatId, serverMsg.id);
        }
      } catch (err) {
        setError(err.message || "Could not rewind the conversation.");
        return;
      }
    }

    setMessages(base);
    await handleSend(text, base);
  };

  const handleChecklist = async () => {
    setToolLoading(true);
    setError(null);
    try {
      setChecklistResult(
        await createChecklist({ visa_type: visaType, details: checklistDetails })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setToolLoading(false);
    }
  };

  const handleRFE = async () => {
    if (rfeText.length < 10) return;
    setToolLoading(true);
    setError(null);
    try {
      setRfeResult(await analyzeRFE({ rfe_text: rfeText }));
    } catch (err) {
      setError(err.message);
    } finally {
      setToolLoading(false);
    }
  };

  const initials = (() => {
    const raw = (user.name || user.email || "U").trim();
    const parts = raw.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return raw.slice(0, 2).toUpperCase();
  })();

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <aside className={`history-panel ${historyOpen ? "open-mobile" : ""}`}>
        <div className="sidebar-head">
          <div className="brand-mark">
            <div className="mark">Be</div>
            <div>
              <h1>Beacon</h1>
              <p>Immigration guidance</p>
            </div>
          </div>
          <button
            type="button"
            className="sidebar-toggle collapse"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
            onClick={toggleSidebar}
          >
            <SidebarIcon />
          </button>
          <button className="btn btn-ghost mobile-bar" onClick={() => setHistoryOpen(false)}>
            Close
          </button>
        </div>

        <button type="button" className="sidebar-new-chat" onClick={startNewChat}>
          <span className="sidebar-new-icon" aria-hidden="true">+</span>
          New chat
        </button>

        <div className="history-list">
          {historyLoading && <p className="history-empty">Loading conversations…</p>}
          {!historyLoading && history.length === 0 && (
            <p className="history-empty">Your conversations will appear here.</p>
          )}
          {groupHistory(history).map((group) => (
            <div key={group.label} className="history-group">
              <p className="history-group-label">{group.label}</p>
              {group.items.map((item) => (
                <div key={item.id} className="history-row">
                  <button
                    className={`history-item ${item.id === activeChatId ? "active" : ""}`}
                    onClick={() => openChat(item.id)}
                    title={item.title}
                  >
                    <span className="title">{item.title}</span>
                  </button>
                  <button
                    type="button"
                    className="history-delete"
                    title="Delete conversation"
                    aria-label={`Delete ${item.title}`}
                    onClick={async () => {
                      if (!confirm("Delete this conversation?")) return;
                      try {
                        await deleteConversation(item.id);
                        if (activeChatId === item.id) startNewChat();
                        const convData = await listConversations();
                        setHistory(convData.conversations || []);
                      } catch (err) {
                        setError(err.message || "Failed to delete conversation");
                      }
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="account-menu" ref={menuRef}>
            <button className="user-chip sidebar-user" onClick={() => setMenuOpen((v) => !v)}>
              {user.picture ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={user.picture} alt="" className="avatar-img" />
              ) : (
                <span className="avatar">{initials}</span>
              )}
              <span className="sidebar-user-meta">
                <strong>{user.name || "Account"}</strong>
                <small>{user.email}</small>
              </span>
            </button>
            {menuOpen && (
              <div className="menu-dropdown up">
                <Link href="/settings" className="menu-item" onClick={() => setMenuOpen(false)}>
                  Profile &amp; API keys
                </Link>
                <button className="menu-item" onClick={handleSignOut}>
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      <div className="main-panel">
        <header className="topbar">
          {sidebarCollapsed && (
            <button
              type="button"
              className="sidebar-toggle expand"
              title="Open sidebar"
              aria-label="Open sidebar"
              onClick={toggleSidebar}
            >
              <SidebarIcon />
            </button>
          )}
          <div className="mobile-bar">
            <button className="btn btn-ghost" onClick={() => setHistoryOpen(true)}>
              History
            </button>
          </div>

          <nav className="nav-tabs" aria-label="Primary">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={`nav-tab ${tab === t.id ? "active" : ""}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>

          <div className="topbar-right">
            {tab === "chat" && (
              <div className="model-selects">
                <select
                  className="select compact"
                  value={provider}
                  onChange={(e) => {
                    const next = e.target.value;
                    setProvider(next);
                    const first = configuredCatalog.find((c) => c.id === next)?.models?.[0]?.id || "";
                    setModel(first);
                  }}
                >
                  <option value="">Provider</option>
                  {configuredCatalog.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
                <select
                  className="select compact"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  disabled={!provider}
                >
                  <option value="">Model</option>
                  {modelsForProvider.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </header>

        <main className={`content ${tab === "chat" ? "has-composer" : ""}`}>
          <div className="content-inner">
          {error && (
            <div className="error-banner">
              <span>{error}</span>
              <button type="button" className="banner-dismiss" onClick={() => setError(null)} aria-label="Dismiss">
                ×
              </button>
            </div>
          )}
          {configuredCatalog.length === 0 && (
            <div className="info-banner">
              No provider API keys yet.{" "}
              <Link href="/settings">Add keys in Settings</Link> to start chatting.
            </div>
          )}

          {tab === "chat" && (
            <>
              {messages.length === 0 ? (
                <section className="hero-block">
                  <h2>Ask clearly. Decide calmly.</h2>
                  <p>
                    Get grounded answers on visas, documents, timelines, and RFEs — with sources
                    you can check.
                  </p>
                  <div className="quick-grid">
                    {QUICK_QUESTIONS.map((q) => (
                      <button key={q} className="quick-btn" onClick={() => handleSend(q)}>
                        {q}
                      </button>
                    ))}
                  </div>
                </section>
              ) : (
                <div className="messages">
                  {messages.map((msg, i) => (
                    <div key={i} className={`msg-block ${msg.role}`}>
                      {editingIdx === i ? (
                        <div className="bubble user msg-editing">
                          <textarea
                            className="msg-edit-area"
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                saveEditAndRerun();
                              }
                              if (e.key === "Escape") cancelEdit();
                            }}
                            rows={Math.min(8, Math.max(2, editText.split("\n").length))}
                            autoFocus
                          />
                          <div className="msg-edit-actions">
                            <button
                              type="button"
                              className="btn btn-primary compact-btn"
                              onClick={saveEditAndRerun}
                              disabled={!editText.trim() || chatLoading}
                            >
                              Save &amp; send
                            </button>
                            <button type="button" className="btn btn-ghost compact-btn" onClick={cancelEdit}>
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className={`bubble ${msg.role}`}>
                            {msg.role === "assistant" ? (
                              <ReactMarkdown components={markdownComponents}>
                                {msg.content}
                              </ReactMarkdown>
                            ) : (
                              msg.content
                            )}
                            {msg.meta?.sources?.length > 0 && (
                              <SourceChips sources={msg.meta.sources} />
                            )}
                          </div>
                          <div className="msg-actions">
                            <button
                              type="button"
                              className="msg-action"
                              onClick={() => copyMessage(msg.content, i)}
                            >
                              {copiedIdx === i ? "Copied" : "Copy"}
                            </button>
                            {msg.role === "user" && (
                              <button
                                type="button"
                                className="msg-action"
                                onClick={() => startEdit(i)}
                                disabled={chatLoading}
                              >
                                Edit
                              </button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                  {chatLoading && <ChatThinking />}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </>
          )}

          {tab === "checklist" && (
            <section className="panel-stack">
              <h2 className="section-title">Document checklist</h2>
              <select className="select" value={visaType} onChange={(e) => setVisaType(e.target.value)}>
                {VISA_TYPES.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
              <textarea
                className="field"
                rows={4}
                value={checklistDetails}
                onChange={(e) => setChecklistDetails(e.target.value)}
                placeholder="Describe your situation…"
              />
              <div>
                <button className="btn btn-primary" onClick={handleChecklist} disabled={toolLoading}>
                  {toolLoading && tab === "checklist" ? "Generating…" : "Generate checklist"}
                </button>
              </div>
              {checklistResult && (
                <div className="result-block">
                  <h3>
                    {checklistResult.visa_type} — {checklistResult.form_number}
                  </h3>
                  {checklistResult?.checklist?.map((cat, i) => (
                    <div key={i} className="category">
                      <h4>{cat.category}</h4>
                      <ul>
                        {cat.items.map((item, j) => (
                          <li key={j}>
                            <strong>{item.document}</strong> — {item.description}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {tab === "timeline" && <UscisTimeline />}

          {tab === "rfe" && (
            <section className="panel-stack">
              <h2 className="section-title">RFE analysis</h2>
              <textarea
                className="field"
                rows={10}
                value={rfeText}
                onChange={(e) => setRfeText(e.target.value)}
                placeholder="Paste your RFE notice text here…"
              />
              <button
                className="btn btn-primary"
                onClick={handleRFE}
                disabled={toolLoading || rfeText.trim().length < 10}
              >
                {toolLoading && tab === "rfe" ? "Analyzing…" : "Analyze RFE"}
              </button>
              {rfeText.trim().length > 0 && rfeText.trim().length < 10 ? (
                <p className="field-hint">Paste at least a short RFE excerpt (10+ characters).</p>
              ) : null}
              {rfeResult && (
                <div className="result-block">
                  <ReactMarkdown components={markdownComponents}>{rfeResult.summary}</ReactMarkdown>
                </div>
              )}
            </section>
          )}
          </div>
        </main>

        {tab === "chat" && (
          <div className="composer">
            <div className="composer-inner">
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask about visas, documents, timelines…"
              />
              <button
                className="btn btn-primary"
                onClick={() => handleSend()}
                disabled={!input.trim() || chatLoading}
              >
                Send
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
