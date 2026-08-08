"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { useAuth } from "../lib/auth";
import ChatThinking from "../components/ChatThinking";
import CaseProfileCard from "../components/CaseProfileCard";
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
  estimateTimeline,
  getHealthReady,
  listConversations,
  sendChatMessageStream,
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
  { id: "H1B", label: "H-1B" },
  { id: "H4", label: "H-4" },
  { id: "H4_EAD", label: "H-4 EAD" },
  { id: "L1A", label: "L-1A" },
  { id: "L1B", label: "L-1B" },
  { id: "O1", label: "O-1" },
  { id: "EB1", label: "EB-1" },
  { id: "EB2", label: "EB-2" },
  { id: "EB3", label: "EB-3" },
  { id: "EB2_NIW", label: "EB-2 NIW" },
  { id: "F1", label: "F-1" },
  { id: "F1_OPT", label: "F-1 OPT" },
  { id: "F1_STEM_OPT", label: "F-1 STEM OPT" },
  { id: "I-485", label: "I-485" },
  { id: "I-130", label: "I-130" },
  { id: "I-140", label: "I-140" },
  { id: "K1", label: "K-1" },
  { id: "TN", label: "TN" },
  { id: "OTHER", label: "Other" },
];

function UscisTimeline() {
  const [forms, setForms] = useState([]);
  const [categories, setCategories] = useState([]);
  const [offices, setOffices] = useState([]);
  const [form, setForm] = useState("");
  const [category, setCategory] = useState("");
  const [office, setOffice] = useState("");
  const [result, setResult] = useState(null);
  const [explain, setExplain] = useState(null);
  const [loading, setLoading] = useState(false);
  const [explaining, setExplaining] = useState(false);
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
    setExplain(null);
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
    setExplain(null);
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
    setExplain(null);
    try {
      setResult(await getUscisProcessingTime(form, category, office));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const onExplain = async () => {
    if (!form || explaining) return;
    setExplaining(true);
    setError("");
    try {
      const catLabel = categories.find((c) => c.id === category)?.description || category;
      const data = await estimateTimeline({
        form_type: form,
        category: category || catLabel,
        filing_date: null,
      });
      setExplain(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setExplaining(false);
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
          {result.months != null ? (
            <div className="pt-explain-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={onExplain}
                disabled={explaining}
              >
                {explaining ? "Explaining…" : "Explain this timeline"}
              </button>
            </div>
          ) : null}
          {explain ? (
            <div className="pt-explain">
              <p>{explain.status_explanation}</p>
              {explain.official_months != null ? (
                <p className="pt-explain-meta">
                  Grounded in USCIS {explain.data_source} figure: {explain.official_months} months
                  {explain.data_as_of ? ` (as of ${explain.data_as_of})` : ""}.
                </p>
              ) : null}
              {explain.options_if_delayed?.length ? (
                <ul>
                  {explain.options_if_delayed.map((o, i) => (
                    <li key={i}>{o}</li>
                  ))}
                </ul>
              ) : null}
              {explain.disclaimer ? <p className="pt-explain-meta">{explain.disclaimer}</p> : null}
            </div>
          ) : null}
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
  const [expanded, setExpanded] = useState(null);
  if (!sources?.length) return null;

  return (
    <div className="sources">
      {sources.map((s, j) => {
        const label = typeof s === "string" ? s : s?.label || "Source";
        const url = typeof s === "string" ? "" : s?.url || "";
        const excerpt = typeof s === "string" ? "" : s?.excerpt || "";
        const isOpen = expanded === j;
        return (
          <div key={j} className="source-item">
            <div className="source-item-row">
              {url ? (
                <a
                  className="source-chip source-link"
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={url}
                >
                  {label}
                </a>
              ) : (
                <span className="source-chip">{label}</span>
              )}
              {excerpt ? (
                <button
                  type="button"
                  className="source-excerpt-toggle"
                  aria-expanded={isOpen}
                  onClick={() => setExpanded(isOpen ? null : j)}
                >
                  {isOpen ? "Hide excerpt" : "Show excerpt"}
                </button>
              ) : null}
            </div>
            {isOpen && excerpt ? (
              <p className="source-excerpt">{excerpt}</p>
            ) : null}
          </div>
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
  const [rfePetition, setRfePetition] = useState("");
  const [kbInfo, setKbInfo] = useState(null);
  const [caseProfile, setCaseProfile] = useState(null);
  const streamAbortRef = useRef(null);

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
    getHealthReady()
      .then((h) =>
        setKbInfo({
          mode: h.knowledge_base_mode || "sample",
          docs: h.knowledge_base_documents ?? 0,
        })
      )
      .catch(() => setKbInfo(null));
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

  const stopStreaming = () => {
    streamAbortRef.current?.abort?.();
    streamAbortRef.current = null;
    setChatLoading(false);
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
    const next = [...base, userMessage, { role: "assistant", content: "", meta: { streaming: true } }];
    setMessages(next);
    setInput("");
    sessionStorage.removeItem(draftKey);
    setChatLoading(true);

    const assistantIdx = next.length - 1;
    let finalSources = [];
    let conversationId = activeChatId;

    const { promise, abort } = sendChatMessageStream({
      message: text,
      chatHistory: base,
      conversationId: activeChatId,
      provider,
      model,
      onEvent: (event) => {
        if (event.type === "start" && event.conversation_id) {
          conversationId = event.conversation_id;
          setActiveChatId(event.conversation_id);
        }
        if (event.type === "sources") {
          finalSources = event.sources || [];
        }
        if (event.type === "token" && event.text) {
          setMessages((prev) => {
            const copy = [...prev];
            const cur = copy[assistantIdx] || { role: "assistant", content: "", meta: {} };
            copy[assistantIdx] = {
              ...cur,
              content: (cur.content || "") + event.text,
              meta: { ...cur.meta, streaming: true },
            };
            return copy;
          });
        }
        if (event.type === "replace" && event.text != null) {
          setMessages((prev) => {
            const copy = [...prev];
            copy[assistantIdx] = {
              role: "assistant",
              content: event.text,
              meta: { streaming: true },
            };
            return copy;
          });
        }
        if (event.type === "done") {
          finalSources = event.sources || finalSources;
          conversationId = event.conversation_id || conversationId;
          setMessages((prev) => {
            const copy = [...prev];
            copy[assistantIdx] = {
              role: "assistant",
              content: event.response || copy[assistantIdx]?.content || "",
              meta: {
                intent: event.intent,
                model: event.model_used,
                provider: event.provider,
                sources: finalSources,
                streaming: false,
              },
            };
            return copy;
          });
          if (conversationId) setActiveChatId(conversationId);
        }
        if (event.type === "error") {
          setError(event.message || "Chat stream failed");
        }
      },
    });
    streamAbortRef.current = { abort };

    try {
      await promise;
      const convData = await listConversations();
      setHistory(convData.conversations || []);
    } catch (err) {
      if (err.name === "AbortError") {
        setMessages((prev) => {
          const copy = [...prev];
          const cur = copy[assistantIdx];
          if (cur && !cur.content) {
            copy[assistantIdx] = {
              role: "assistant",
              content: "_(Generation stopped.)_",
              meta: { streaming: false },
            };
          } else if (cur) {
            copy[assistantIdx] = { ...cur, meta: { ...cur.meta, streaming: false } };
          }
          return copy;
        });
        return;
      }
      if (err.status === 401) {
        setError("Session expired. Please sign in again.");
        await handleSignOut();
        return;
      }
      setError(err.message);
      setMessages((prev) => {
        const copy = [...prev];
        if (!copy[assistantIdx]?.content) {
          return copy.filter((_, i) => i !== assistantIdx);
        }
        copy[assistantIdx] = {
          ...copy[assistantIdx],
          meta: { ...copy[assistantIdx].meta, streaming: false },
        };
        return copy;
      });
    } finally {
      streamAbortRef.current = null;
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
        await createChecklist({
          visa_type: visaType,
          details: checklistDetails,
          has_dependents: !!caseProfile?.has_dependents,
          is_premium_processing: !!caseProfile?.premium_processing,
          form_number: caseProfile?.form_number || undefined,
          service_center: caseProfile?.service_center || undefined,
          employer_name: caseProfile?.employer_name || undefined,
          use_case_profile: true,
        })
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
      const petition = rfePetition || caseProfile?.visa_type || undefined;
      setRfeResult(
        await analyzeRFE({
          rfe_text: rfeText,
          petition_type: petition || undefined,
          additional_context: caseProfile?.notes || "",
          use_case_profile: true,
        })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setToolLoading(false);
    }
  };

  const applyProfileToTools = useCallback((profile) => {
    setCaseProfile(profile);
    if (profile?.visa_type) {
      setVisaType(profile.visa_type);
      setRfePetition(profile.visa_type);
    }
  }, []);

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
          {kbInfo ? (
            <p
              className={`kb-badge ${kbInfo.mode === "sample" ? "sample" : "ready"}`}
              title="Answers cite the knowledge base. Sample mode means curated starter docs; scrape expands coverage."
            >
              Knowledge: {kbInfo.mode === "sample" ? "sample" : kbInfo.mode} · {kbInfo.docs} docs
            </p>
          ) : null}
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

          <CaseProfileCard onChange={applyProfileToTools} compact />

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
                  {chatLoading &&
                    !(
                      messages[messages.length - 1]?.role === "assistant" &&
                      messages[messages.length - 1]?.content
                    ) && <ChatThinking />}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </>
          )}

          {tab === "checklist" && (
            <section className="panel-stack">
              <h2 className="section-title">Document checklist</h2>
              <p className="field-hint">
                Uses your case profile (dependents, premium processing, employer) when saved.
              </p>
              <select className="select" value={visaType} onChange={(e) => setVisaType(e.target.value)}>
                {VISA_TYPES.map((v) => (
                  <option key={v.id} value={v.id}>{v.label}</option>
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
                <div className="result-block checklist-result">
                  <div className="result-header-row">
                    <h3>
                      {checklistResult.visa_type} — {checklistResult.form_number}
                    </h3>
                    {checklistResult.profile_applied ? (
                      <span className="pill soft">Profile applied</span>
                    ) : null}
                  </div>
                  <p className="meta-line">
                    Fee: {checklistResult.filing_fee} · Prep: {checklistResult.estimated_prep_time}
                    {checklistResult.filing_methods?.length
                      ? ` · Filing: ${checklistResult.filing_methods.join(", ")}`
                      : ""}
                  </p>
                  {checklistResult?.checklist?.map((cat, i) => (
                    <div key={i} className="category">
                      <h4>{cat.category}</h4>
                      <ul className="checklist-items">
                        {cat.items.map((item, j) => (
                          <li key={j}>
                            <div className="item-title">
                              <strong>{item.document}</strong>
                              <span className={`pill ${item.required ? "req" : "opt"}`}>
                                {item.required ? "Required" : "Optional"}
                              </span>
                            </div>
                            {item.description ? <p>{item.description}</p> : null}
                            {item.why_needed ? (
                              <p className="why-needed"><em>Why:</em> {item.why_needed}</p>
                            ) : null}
                            {item.tips ? <p className="tip">Tip: {item.tips}</p> : null}
                            {item.source_hint ? (
                              <p className="source-hint">Source cue: {item.source_hint}</p>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                  {checklistResult.common_mistakes?.length > 0 && (
                    <div className="mistakes">
                      <h4>Common mistakes</h4>
                      <ul>
                        {checklistResult.common_mistakes.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {checklistResult.missing_if_dependents?.length > 0 && (
                    <div className="mistakes">
                      <h4>If you have dependents</h4>
                      <ul>
                        {checklistResult.missing_if_dependents.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {checklistResult.sources?.length > 0 && (
                    <SourceChips sources={checklistResult.sources} />
                  )}
                  {checklistResult.disclaimer ? (
                    <p className="disclaimer-line">{checklistResult.disclaimer}</p>
                  ) : null}
                </div>
              )}
            </section>
          )}

          {tab === "timeline" && <UscisTimeline />}

          {tab === "rfe" && (
            <section className="panel-stack">
              <h2 className="section-title">RFE analysis</h2>
              <p className="field-hint">
                Point-by-point breakdown with evidence suggestions — not a drafted legal response.
              </p>
              <select
                className="select"
                value={rfePetition || ""}
                onChange={(e) => setRfePetition(e.target.value)}
              >
                <option value="">Petition type (optional)</option>
                {VISA_TYPES.map((v) => (
                  <option key={v.id} value={v.id}>{v.label}</option>
                ))}
              </select>
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
                <div className="result-block rfe-result">
                  <div className="result-header-row">
                    <h3>Analysis</h3>
                    <span className={`pill risk-${(rfeResult.risk_level || "moderate").toLowerCase()}`}>
                      {rfeResult.risk_level || "moderate"}
                    </span>
                    {rfeResult.profile_applied ? (
                      <span className="pill soft">Profile applied</span>
                    ) : null}
                  </div>
                  {rfeResult.deadline_info ? (
                    <p className="deadline"><strong>Deadline:</strong> {rfeResult.deadline_info}</p>
                  ) : null}
                  <div className="rfe-summary">
                    <ReactMarkdown components={markdownComponents}>{rfeResult.summary}</ReactMarkdown>
                  </div>
                  {rfeResult.points?.length > 0 && (
                    <div className="rfe-points">
                      <h4>Points raised</h4>
                      {rfeResult.points.map((p, i) => (
                        <article key={i} className="rfe-point">
                          <div className="item-title">
                            <strong>{p.issue}</strong>
                            {p.severity ? (
                              <span className={`pill risk-${p.severity.toLowerCase()}`}>{p.severity}</span>
                            ) : null}
                          </div>
                          {p.what_uscis_wants ? <p>{p.what_uscis_wants}</p> : null}
                          {p.evidence_suggestions?.length > 0 && (
                            <ul>
                              {p.evidence_suggestions.map((s, j) => (
                                <li key={j}>{s}</li>
                              ))}
                            </ul>
                          )}
                          {p.policy_anchor ? (
                            <p className="source-hint">Policy cue: {p.policy_anchor}</p>
                          ) : null}
                        </article>
                      ))}
                    </div>
                  )}
                  {rfeResult.response_outline?.length > 0 && (
                    <div>
                      <h4>Response outline</h4>
                      <ol>
                        {rfeResult.response_outline.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                  {rfeResult.next_steps?.length > 0 && (
                    <div>
                      <h4>Next steps</h4>
                      <ul>
                        {rfeResult.next_steps.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {rfeResult.sources?.length > 0 && (
                    <SourceChips sources={rfeResult.sources} />
                  )}
                  {rfeResult.disclaimer ? (
                    <p className="disclaimer-line">{rfeResult.disclaimer}</p>
                  ) : null}
                </div>
              )}
            </section>
          )}
          </div>
        </main>

        {tab === "chat" && (
          <div className="composer">
            <div className="composer-inner">
              {chatLoading ? (
                <button type="button" className="btn btn-ghost stop-stream" onClick={stopStreaming}>
                  Stop
                </button>
              ) : null}
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
