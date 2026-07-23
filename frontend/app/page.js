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
  estimateTimeline,
  getConversation,
  getSettingsPreferences,
  listConversations,
  sendChatMessage,
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

const SERVICE_CENTERS = [
  "California Service Center",
  "Nebraska Service Center",
  "Texas Service Center",
  "Vermont Service Center",
  "Potomac Service Center",
  "National Benefits Center",
];

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function Home() {
  const { user, loading, signOut } = useAuth();
  const [tab, setTab] = useState("chat");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [prefs, setPrefs] = useState(null);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);
  const draftKey = "immi_draft_message";

  const [visaType, setVisaType] = useState("H1B");
  const [checklistDetails, setChecklistDetails] = useState("");
  const [checklistResult, setChecklistResult] = useState(null);
  const [formType, setFormType] = useState("I-129");
  const [serviceCenter, setServiceCenter] = useState(SERVICE_CENTERS[0]);
  const [filingDate, setFilingDate] = useState("");
  const [timelineResult, setTimelineResult] = useState(null);
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
    if (!user) return;
    const draft = sessionStorage.getItem(draftKey);
    if (draft) setInput(draft);
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
  }, [messages, tab]);

  useEffect(() => {
    sessionStorage.setItem(draftKey, input);
  }, [input]);

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

  const handleSend = async (messageText = null) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;
    if (!provider || !model) {
      setError("Select a provider/model in the selector, or add API keys in Settings.");
      return;
    }
    setError(null);
    const userMessage = { role: "user", content: text };
    const next = [...messages, userMessage];
    setMessages(next);
    setInput("");
    sessionStorage.removeItem(draftKey);
    setIsLoading(true);

    try {
      const response = await sendChatMessage({
        message: text,
        chatHistory: messages,
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
      setIsLoading(false);
    }
  };

  const handleChecklist = async () => {
    setIsLoading(true);
    setError(null);
    try {
      setChecklistResult(
        await createChecklist({ visa_type: visaType, details: checklistDetails })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTimeline = async () => {
    setIsLoading(true);
    setError(null);
    try {
      setTimelineResult(
        await estimateTimeline({
          form_type: formType,
          service_center: serviceCenter,
          filing_date: filingDate || null,
        })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRFE = async () => {
    if (rfeText.length < 10) return;
    setIsLoading(true);
    setError(null);
    try {
      setRfeResult(await analyzeRFE({ rfe_text: rfeText }));
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const initials = (user.name || user.email || "U")
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="app-shell">
      <aside className={`history-panel ${historyOpen ? "open-mobile" : ""}`}>
        <div className="brand-mark">
          <div className="mark">IA</div>
          <div>
            <h1>ImmiAssist</h1>
            <p>Immigration guidance</p>
          </div>
        </div>

        <div className="history-actions">
          <button className="btn btn-primary" style={{ flex: 1 }} onClick={startNewChat}>
            New chat
          </button>
          <button className="btn btn-ghost mobile-bar" onClick={() => setHistoryOpen(false)}>
            Close
          </button>
        </div>

        <div className="history-list">
          {historyLoading && (
            <p style={{ color: "var(--muted)", fontSize: "0.85rem", padding: "0 4px" }}>
              Loading conversations…
            </p>
          )}
          {!historyLoading && history.length === 0 && (
            <p style={{ color: "var(--muted)", fontSize: "0.85rem", padding: "0 4px" }}>
              Your conversations will appear here.
            </p>
          )}
          {history.map((item) => (
            <div key={item.id} style={{ display: "flex", gap: 4 }}>
              <button
                className={`history-item ${item.id === activeChatId ? "active" : ""}`}
                style={{ flex: 1 }}
                onClick={() => openChat(item.id)}
              >
                <div className="title">{item.title}</div>
                <div className="meta">{formatTime(item.updated_at)}</div>
              </button>
              <button
                className="btn btn-ghost"
                title="Delete"
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
      </aside>

      <div className="main-panel">
        <header className="topbar">
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

            <div className="account-menu" ref={menuRef}>
              <button className="user-chip" onClick={() => setMenuOpen((v) => !v)}>
                {user.picture ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={user.picture} alt="" className="avatar-img" />
                ) : (
                  <span className="avatar">{initials}</span>
                )}
                <span>{user.name || user.email}</span>
              </button>
              {menuOpen && (
                <div className="menu-dropdown">
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
        </header>

        <main className="content">
          {error && <div className="error-banner">{error}</div>}
          {configuredCatalog.length === 0 && (
            <div className="error-banner">
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
                    <div key={i} className={`bubble ${msg.role}`}>
                      {msg.role === "assistant" ? (
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      ) : (
                        msg.content
                      )}
                      {msg.meta?.sources?.length > 0 && (
                        <div className="sources">
                          {msg.meta.sources.slice(0, 4).map((s, j) => (
                            <span key={j} className="source-chip">
                              {s}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                  {isLoading && <ChatThinking />}
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
                <button className="btn btn-primary" onClick={handleChecklist} disabled={isLoading}>
                  Generate checklist
                </button>
              </div>
              {checklistResult && (
                <div className="result-block">
                  <h3>
                    {checklistResult.visa_type} — {checklistResult.form_number}
                  </h3>
                  {checklistResult.checklist.map((cat, i) => (
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

          {tab === "timeline" && (
            <section className="panel-stack">
              <h2 className="section-title">Processing timeline</h2>
              <input className="field" value={formType} onChange={(e) => setFormType(e.target.value)} />
              <select className="select" value={serviceCenter} onChange={(e) => setServiceCenter(e.target.value)}>
                {SERVICE_CENTERS.map((sc) => (
                  <option key={sc} value={sc}>{sc}</option>
                ))}
              </select>
              <input className="field" type="date" value={filingDate} onChange={(e) => setFilingDate(e.target.value)} />
              <button className="btn btn-primary" onClick={handleTimeline} disabled={isLoading}>
                Estimate timeline
              </button>
              {timelineResult && (
                <div className="result-block">
                  <h3>{timelineResult.form_type}</h3>
                  <p>{timelineResult.status_explanation}</p>
                </div>
              )}
            </section>
          )}

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
              <button className="btn btn-primary" onClick={handleRFE} disabled={isLoading || rfeText.length < 10}>
                Analyze RFE
              </button>
              {rfeResult && (
                <div className="result-block">
                  <ReactMarkdown>{rfeResult.summary}</ReactMarkdown>
                </div>
              )}
            </section>
          )}
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
                disabled={!input.trim() || isLoading}
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
