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

const TABS = ["chat", "checklist", "timeline", "rfe"];

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

const styles = {
  page: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
    color: "#e2e8f0",
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    borderBottom: "1px solid #334155",
    padding: "16px 24px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "rgba(15, 23, 42, 0.9)",
    position: "sticky",
    top: 0,
    zIndex: 10,
  },
  tab: (active) => ({
    padding: "8px 16px",
    borderRadius: 8,
    border: "none",
    cursor: "pointer",
    background: active ? "#3b82f6" : "transparent",
    color: active ? "#fff" : "#94a3b8",
    fontWeight: active ? 600 : 400,
  }),
  card: {
    background: "rgba(51, 65, 85, 0.5)",
    border: "1px solid #475569",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  input: {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 10,
    border: "1px solid #475569",
    background: "rgba(30, 41, 59, 0.8)",
    color: "#e2e8f0",
    fontSize: 14,
    marginBottom: 10,
  },
  button: {
    padding: "12px 20px",
    borderRadius: 10,
    border: "none",
    background: "linear-gradient(135deg, #3b82f6, #2563eb)",
    color: "#fff",
    cursor: "pointer",
    fontWeight: 600,
  },
};

export default function Home() {
  const [tab, setTab] = useState("chat");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  // Checklist state
  const [visaType, setVisaType] = useState("H1B");
  const [checklistDetails, setChecklistDetails] = useState("");
  const [checklistResult, setChecklistResult] = useState(null);

  // Timeline state
  const [formType, setFormType] = useState("I-129");
  const [serviceCenter, setServiceCenter] = useState(SERVICE_CENTERS[0]);
  const [filingDate, setFilingDate] = useState("");
  const [timelineResult, setTimelineResult] = useState(null);

  // RFE state
  const [rfeText, setRfeText] = useState("");
  const [rfeResult, setRfeResult] = useState(null);

  useEffect(() => {
    setApiKeyInput(getStoredApiKey());
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSaveApiKey = () => {
    setApiKey(apiKeyInput);
    setError(null);
  };

  const handleRegister = async () => {
    try {
      const result = await registerUser(null, "starter");
      setApiKeyInput(result.api_key);
      setApiKey(result.api_key);
      setError(null);
      alert(`API key created. Daily limit: ${result.daily_limit}`);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleSend = async (messageText = null) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setIsLoading(true);
    try {
      const sessionId =
        typeof window !== "undefined"
          ? localStorage.getItem("immi_chat_session_id")
          : null;
      const response = await sendChatMessage(text, messages, sessionId);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.response,
          meta: {
            intent: response.intent,
            model: response.model_used,
            sources: response.sources,
          },
        },
      ]);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChecklist = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await createChecklist({
        visa_type: visaType,
        details: checklistDetails,
      });
      setChecklistResult(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTimeline = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await estimateTimeline({
        form_type: formType,
        service_center: serviceCenter,
        filing_date: filingDate || null,
      });
      setTimelineResult(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRFE = async () => {
    if (rfeText.length < 10) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await analyzeRFE({ rfe_text: rfeText });
      setRfeResult(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 28 }}>🇺🇸</span>
          <div>
            <h1 style={{ margin: 0, fontSize: 20 }}>ImmiAssist AI</h1>
            <p style={{ margin: 0, fontSize: 12, color: "#94a3b8" }}>
              Production immigration assistant
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="password"
            placeholder="API Key (optional)"
            value={apiKeyInput}
            onChange={(e) => setApiKeyInput(e.target.value)}
            style={{ ...styles.input, width: 180, marginBottom: 0 }}
          />
          <button style={{ ...styles.button, padding: "8px 12px" }} onClick={handleSaveApiKey}>
            Save
          </button>
          <button
            style={{ ...styles.button, padding: "8px 12px", background: "#475569" }}
            onClick={handleRegister}
          >
            Get Key
          </button>
        </div>
      </header>

      <nav style={{ display: "flex", gap: 8, padding: "12px 24px", borderBottom: "1px solid #334155" }}>
        {TABS.map((t) => (
          <button key={t} style={styles.tab(tab === t)} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>

      <main style={{ maxWidth: 800, margin: "0 auto", padding: "24px 16px 80px" }}>
        {error && (
          <div style={{ ...styles.card, borderColor: "#ef4444", color: "#fca5a5" }}>
            {error}
          </div>
        )}

        {tab === "chat" && (
          <>
            {messages.length === 0 ? (
              <div style={{ textAlign: "center", paddingTop: 40 }}>
                <h2>Immigration Q&A</h2>
                <p style={{ color: "#94a3b8" }}>Ask about visas, documents, timelines, and more.</p>
                <div style={{ display: "grid", gap: 10, marginTop: 24 }}>
                  {QUICK_QUESTIONS.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(q)}
                      style={{ ...styles.card, cursor: "pointer", textAlign: "left" }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    style={{
                      alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                      maxWidth: "90%",
                      ...styles.card,
                      background:
                        msg.role === "user"
                          ? "linear-gradient(135deg, #3b82f6, #2563eb)"
                          : styles.card.background,
                    }}
                  >
                    {msg.role === "assistant" ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      msg.content
                    )}
                    {msg.meta?.sources?.length > 0 && (
                      <div style={{ marginTop: 8, fontSize: 11, color: "#93c5fd" }}>
                        {msg.meta.sources.slice(0, 3).map((s, j) => (
                          <div key={j}>📄 {s}</div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
            <div style={{ position: "fixed", bottom: 0, left: 0, right: 0, padding: 16, background: "rgba(15,23,42,0.95)" }}>
              <div style={{ maxWidth: 800, margin: "0 auto", display: "flex", gap: 8 }}>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder="Ask an immigration question..."
                  style={{ ...styles.input, marginBottom: 0, flex: 1 }}
                />
                <button style={styles.button} onClick={() => handleSend()} disabled={isLoading}>
                  Send
                </button>
              </div>
            </div>
          </>
        )}

        {tab === "checklist" && (
          <div>
            <h2>Document Checklist</h2>
            <select value={visaType} onChange={(e) => setVisaType(e.target.value)} style={styles.input}>
              {VISA_TYPES.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            <textarea
              value={checklistDetails}
              onChange={(e) => setChecklistDetails(e.target.value)}
              placeholder="Describe your situation..."
              rows={4}
              style={styles.input}
            />
            <button style={styles.button} onClick={handleChecklist} disabled={isLoading}>
              Generate Checklist
            </button>
            {checklistResult && (
              <div style={{ marginTop: 24 }}>
                <h3>{checklistResult.visa_type} — {checklistResult.form_number}</h3>
                <p>Fee: {checklistResult.filing_fee} | Prep time: {checklistResult.estimated_prep_time}</p>
                {checklistResult.checklist.map((cat, i) => (
                  <div key={i} style={styles.card}>
                    <strong>{cat.category}</strong>
                    <ul>
                      {cat.items.map((item, j) => (
                        <li key={j}>
                          {item.required ? "✅" : "○"} {item.document} — {item.description}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
                <p style={{ fontSize: 12, color: "#94a3b8" }}>{checklistResult.disclaimer}</p>
              </div>
            )}
          </div>
        )}

        {tab === "timeline" && (
          <div>
            <h2>Processing Timeline</h2>
            <input
              value={formType}
              onChange={(e) => setFormType(e.target.value)}
              placeholder="Form type (e.g. I-129)"
              style={styles.input}
            />
            <select
              value={serviceCenter}
              onChange={(e) => setServiceCenter(e.target.value)}
              style={styles.input}
            >
              {SERVICE_CENTERS.map((sc) => (
                <option key={sc} value={sc}>{sc}</option>
              ))}
            </select>
            <input
              type="date"
              value={filingDate}
              onChange={(e) => setFilingDate(e.target.value)}
              style={styles.input}
            />
            <button style={styles.button} onClick={handleTimeline} disabled={isLoading}>
              Estimate Timeline
            </button>
            {timelineResult && (
              <div style={{ marginTop: 24, ...styles.card }}>
                <h3>{timelineResult.form_type}</h3>
                <p>Status: <strong>{timelineResult.case_status}</strong></p>
                <p>{timelineResult.status_explanation}</p>
                <p>
                  Range: {timelineResult.processing_range_months?.min}–
                  {timelineResult.processing_range_months?.max} months
                </p>
                <p style={{ fontSize: 12 }}>{timelineResult.disclaimer}</p>
              </div>
            )}
          </div>
        )}

        {tab === "rfe" && (
          <div>
            <h2>RFE Analysis</h2>
            <textarea
              value={rfeText}
              onChange={(e) => setRfeText(e.target.value)}
              placeholder="Paste your RFE notice text here..."
              rows={10}
              style={styles.input}
            />
            <button style={styles.button} onClick={handleRFE} disabled={isLoading || rfeText.length < 10}>
              Analyze RFE
            </button>
            {rfeResult && (
              <div style={{ marginTop: 24 }}>
                <div style={styles.card}>
                  <h3>Summary</h3>
                  <ReactMarkdown>{rfeResult.summary}</ReactMarkdown>
                  <p><strong>Risk:</strong> {rfeResult.risk_level}</p>
                  <p><strong>Deadline:</strong> {rfeResult.deadline_info}</p>
                </div>
                {rfeResult.points?.map((p, i) => (
                  <div key={i} style={styles.card}>
                    <strong>{p.issue}</strong>
                    <ul>
                      {p.evidence_suggestions?.map((s, j) => (
                        <li key={j}>{s}</li>
                      ))}
                    </ul>
                  </div>
                ))}
                <p style={{ fontSize: 12, color: "#94a3b8" }}>{rfeResult.disclaimer}</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
