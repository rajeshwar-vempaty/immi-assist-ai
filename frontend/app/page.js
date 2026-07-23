"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import {
  sendChatMessage,
  createChecklist,
  estimateTimeline,
  analyzeRFE,
  registerUser,
  setApiKey,
  getStoredApiKey,
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

const HISTORY_KEY = "immi_chat_history_v1";
const USER_KEY = "immi_user_profile_v1";

function loadHistory() {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveHistory(items) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 40)));
}

function loadUser() {
  if (typeof window === "undefined") return null;
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

function saveUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  else localStorage.removeItem(USER_KEY);
}

function titleFromMessages(messages) {
  const first = messages.find((m) => m.role === "user");
  if (!first) return "New conversation";
  return first.content.slice(0, 48) + (first.content.length > 48 ? "…" : "");
}

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
  const [tab, setTab] = useState("chat");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [history, setHistory] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const [visaType, setVisaType] = useState("H1B");
  const [checklistDetails, setChecklistDetails] = useState("");
  const [checklistResult, setChecklistResult] = useState(null);

  const [formType, setFormType] = useState("I-129");
  const [serviceCenter, setServiceCenter] = useState(SERVICE_CENTERS[0]);
  const [filingDate, setFilingDate] = useState("");
  const [timelineResult, setTimelineResult] = useState(null);

  const [rfeText, setRfeText] = useState("");
  const [rfeResult, setRfeResult] = useState(null);

  useEffect(() => {
    setApiKeyInput(getStoredApiKey());
    setUser(loadUser());
    const items = loadHistory();
    setHistory(items);
    if (items[0]) {
      setActiveChatId(items[0].id);
      setMessages(items[0].messages || []);
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, tab]);

  const persistConversation = (nextMessages, chatId = activeChatId) => {
    const now = new Date().toISOString();
    let items = loadHistory();
    if (!chatId) {
      const id = crypto.randomUUID();
      const entry = {
        id,
        title: titleFromMessages(nextMessages),
        messages: nextMessages,
        updatedAt: now,
      };
      items = [entry, ...items];
      setActiveChatId(id);
      setHistory(items);
      saveHistory(items);
      return id;
    }
    items = items.map((item) =>
      item.id === chatId
        ? {
            ...item,
            title: titleFromMessages(nextMessages),
            messages: nextMessages,
            updatedAt: now,
          }
        : item
    );
    setHistory(items);
    saveHistory(items);
    return chatId;
  };

  const startNewChat = () => {
    setActiveChatId(null);
    setMessages([]);
    setError(null);
    setTab("chat");
    setHistoryOpen(false);
  };

  const openChat = (id) => {
    const item = history.find((h) => h.id === id);
    if (!item) return;
    setActiveChatId(id);
    setMessages(item.messages || []);
    setTab("chat");
    setHistoryOpen(false);
  };

  const handleSaveApiKey = () => {
    setApiKey(apiKeyInput);
    setError(null);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(null);
    const name = displayName.trim() || email.split("@")[0] || "Guest";
    try {
      // Optional: mint an API key when registering with backend
      let apiKey = getStoredApiKey();
      if (!apiKey && email.trim()) {
        try {
          const result = await registerUser(email.trim(), "free");
          apiKey = result.api_key;
          setApiKey(apiKey);
          setApiKeyInput(apiKey);
        } catch {
          // Public registration may be disabled — still allow local profile UI
        }
      }
      const profile = {
        name,
        email: email.trim() || null,
        signedInAt: new Date().toISOString(),
      };
      saveUser(profile);
      setUser(profile);
      setLoginOpen(false);
    } catch (err) {
      setError(err.message || "Could not sign in");
    }
  };

  const handleSignOut = () => {
    saveUser(null);
    setUser(null);
  };

  const handleSend = async (messageText = null) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;
    setError(null);
    const userMessage = { role: "user", content: text };
    const next = [...messages, userMessage];
    setMessages(next);
    setInput("");
    setIsLoading(true);
    const chatId = persistConversation(next);

    try {
      const sessionId =
        typeof window !== "undefined"
          ? localStorage.getItem("immi_chat_session_id")
          : null;
      const response = await sendChatMessage(text, messages, sessionId);
      const assistantMessage = {
        role: "assistant",
        content: response.response,
        meta: {
          intent: response.intent,
          model: response.model_used,
          sources: response.sources,
        },
      };
      const withAssistant = [...next, assistantMessage];
      setMessages(withAssistant);
      persistConversation(withAssistant, chatId);
    } catch (err) {
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

  const initials = (user?.name || "G")
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
          <button
            className="btn btn-ghost mobile-bar"
            onClick={() => setHistoryOpen(false)}
          >
            Close
          </button>
        </div>

        <div className="history-list">
          {history.length === 0 && (
            <p style={{ color: "var(--muted)", fontSize: "0.85rem", padding: "0 4px" }}>
              Your conversations will appear here.
            </p>
          )}
          {history.map((item) => (
            <button
              key={item.id}
              className={`history-item ${item.id === activeChatId ? "active" : ""}`}
              onClick={() => openChat(item.id)}
            >
              <div className="title">{item.title}</div>
              <div className="meta">{formatTime(item.updatedAt)}</div>
            </button>
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
            {user ? (
              <>
                <div className="user-chip">
                  <span className="avatar">{initials}</span>
                  <span>{user.name}</span>
                </div>
                <button className="btn btn-ghost" onClick={handleSignOut}>
                  Sign out
                </button>
              </>
            ) : (
              <button className="btn btn-ink" onClick={() => setLoginOpen(true)}>
                Sign in
              </button>
            )}
          </div>
        </header>

        <main className={`content ${tab === "chat" ? "" : ""}`}>
          {error && <div className="error-banner">{error}</div>}

          {tab === "chat" && (
            <>
              {messages.length === 0 ? (
                <section className="hero-block">
                  <h2>Ask clearly. Decide calmly.</h2>
                  <p>
                    Get grounded answers on visas, documents, timelines, and RFEs —
                    with sources you can check.
                  </p>
                  <div className="quick-grid">
                    {QUICK_QUESTIONS.map((q) => (
                      <button key={q} className="quick-btn" onClick={() => handleSend(q)}>
                        {q}
                      </button>
                    ))}
                  </div>
                  <p className="disclaimer">
                    Informational guidance only — not legal advice. For your specific
                    case, consult a licensed immigration attorney.
                  </p>
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
                  {isLoading && (
                    <div className="bubble assistant" style={{ color: "var(--muted)" }}>
                      Researching…
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </>
          )}

          {tab === "checklist" && (
            <section className="panel-stack">
              <h2 className="section-title">Document checklist</h2>
              <p className="section-sub">
                Build a filing-ready list for your petition type and situation.
              </p>
              <select
                className="select"
                value={visaType}
                onChange={(e) => setVisaType(e.target.value)}
              >
                {VISA_TYPES.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
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
                  <h3 style={{ marginTop: 0 }}>
                    {checklistResult.visa_type} — {checklistResult.form_number}
                  </h3>
                  <p style={{ color: "var(--muted)" }}>
                    Fee: {checklistResult.filing_fee} · Prep time:{" "}
                    {checklistResult.estimated_prep_time}
                  </p>
                  {checklistResult.checklist.map((cat, i) => (
                    <div key={i} className="category">
                      <h4>{cat.category}</h4>
                      <ul>
                        {cat.items.map((item, j) => (
                          <li key={j}>
                            <strong>{item.document}</strong>
                            {item.required ? " (required)" : " (optional)"} —{" "}
                            {item.description}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                  <p className="disclaimer">{checklistResult.disclaimer}</p>
                </div>
              )}
            </section>
          )}

          {tab === "timeline" && (
            <section className="panel-stack">
              <h2 className="section-title">Processing timeline</h2>
              <p className="section-sub">
                Estimate wait ranges from current USCIS processing-time guidance.
              </p>
              <input
                className="field"
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                placeholder="Form type (e.g. I-129)"
              />
              <select
                className="select"
                value={serviceCenter}
                onChange={(e) => setServiceCenter(e.target.value)}
              >
                {SERVICE_CENTERS.map((sc) => (
                  <option key={sc} value={sc}>
                    {sc}
                  </option>
                ))}
              </select>
              <input
                className="field"
                type="date"
                value={filingDate}
                onChange={(e) => setFilingDate(e.target.value)}
              />
              <div>
                <button className="btn btn-primary" onClick={handleTimeline} disabled={isLoading}>
                  Estimate timeline
                </button>
              </div>
              {timelineResult && (
                <div className="result-block">
                  <h3 style={{ marginTop: 0 }}>{timelineResult.form_type}</h3>
                  <p>
                    Status: <strong>{timelineResult.case_status}</strong>
                  </p>
                  <p>{timelineResult.status_explanation}</p>
                  <p>
                    Range: {timelineResult.processing_range_months?.min}–
                    {timelineResult.processing_range_months?.max} months
                  </p>
                  <p className="disclaimer">{timelineResult.disclaimer}</p>
                </div>
              )}
            </section>
          )}

          {tab === "rfe" && (
            <section className="panel-stack">
              <h2 className="section-title">RFE analysis</h2>
              <p className="section-sub">
                Paste the notice text to break down issues, evidence, and next steps.
              </p>
              <textarea
                className="field"
                rows={10}
                value={rfeText}
                onChange={(e) => setRfeText(e.target.value)}
                placeholder="Paste your RFE notice text here…"
              />
              <div>
                <button
                  className="btn btn-primary"
                  onClick={handleRFE}
                  disabled={isLoading || rfeText.length < 10}
                >
                  Analyze RFE
                </button>
              </div>
              {rfeResult && (
                <div className="result-block">
                  <h3 style={{ marginTop: 0 }}>Summary</h3>
                  <ReactMarkdown>{rfeResult.summary}</ReactMarkdown>
                  <p>
                    <strong>Risk:</strong> {rfeResult.risk_level}
                  </p>
                  <p>
                    <strong>Deadline:</strong> {rfeResult.deadline_info}
                  </p>
                  {rfeResult.points?.map((p, i) => (
                    <div key={i} className="category">
                      <h4>{p.issue}</h4>
                      <ul>
                        {p.evidence_suggestions?.map((s, j) => (
                          <li key={j}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                  <p className="disclaimer">{rfeResult.disclaimer}</p>
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

      {loginOpen && (
        <div className="modal-backdrop" onClick={() => setLoginOpen(false)}>
          <form
            className="modal"
            onClick={(e) => e.stopPropagation()}
            onSubmit={handleLogin}
          >
            <h3>Welcome back</h3>
            <p>
              Sign in to keep your profile handy. Chat history is saved on this device
              for now — account sync comes next.
            </p>
            <input
              className="field"
              style={{ marginBottom: 10 }}
              placeholder="Display name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
            <input
              className="field"
              type="email"
              placeholder="Email (optional)"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <details style={{ marginTop: 12 }}>
              <summary style={{ cursor: "pointer", color: "var(--muted)", fontSize: "0.85rem" }}>
                Advanced: API key
              </summary>
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <input
                  className="field"
                  type="password"
                  placeholder="API key"
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                />
                <button type="button" className="btn btn-ghost" onClick={handleSaveApiKey}>
                  Save
                </button>
              </div>
            </details>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setLoginOpen(false)}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Continue
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
