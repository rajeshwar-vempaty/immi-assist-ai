"use client";

import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../lib/api";

const QUICK_QUESTIONS = [
  "How do I transfer my H-1B to a new employer?",
  "What documents do I need for I-485 filing?",
  "What is the EB-2 NIW process?",
  "My OPT expires in 60 days — what are my options?",
  "How does the H-1B lottery work?",
  "What is premium processing?",
];

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (messageText = null) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;

    const userMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await sendChatMessage(text, messages);
      const assistantMessage = {
        role: "assistant",
        content: response.response,
        meta: {
          intent: response.intent,
          model: response.model_used,
          sources: response.sources,
          confidence: response.confidence,
          requires_lawyer: response.requires_lawyer,
        },
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I'm having trouble connecting right now. Please try again in a moment.",
          meta: { intent: "error", model: "none", sources: [], confidence: 0 },
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        color: "#e2e8f0",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}
    >
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid #334155",
          padding: "16px 24px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          background: "rgba(15, 23, 42, 0.8)",
          backdropFilter: "blur(8px)",
          position: "sticky",
          top: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 10,
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 20,
          }}
        >
          🇺🇸
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>
            ImmiAssist AI
          </h1>
          <p
            style={{
              margin: 0,
              fontSize: 13,
              color: "#94a3b8",
            }}
          >
            Your intelligent immigration assistant
          </p>
        </div>
      </header>

      {/* Messages Area */}
      <main
        style={{
          maxWidth: 800,
          margin: "0 auto",
          padding: "24px 16px 160px",
          minHeight: "calc(100vh - 180px)",
        }}
      >
        {messages.length === 0 ? (
          /* Welcome Screen */
          <div style={{ textAlign: "center", paddingTop: 60 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🗽</div>
            <h2
              style={{
                fontSize: 28,
                fontWeight: 700,
                marginBottom: 8,
                background: "linear-gradient(135deg, #60a5fa, #a78bfa)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Welcome to ImmiAssist AI
            </h2>
            <p
              style={{
                color: "#94a3b8",
                fontSize: 16,
                maxWidth: 500,
                margin: "0 auto 32px",
                lineHeight: 1.6,
              }}
            >
              Get instant answers about US immigration processes, visa types,
              document requirements, and more. Powered by official USCIS
              sources.
            </p>

            {/* Quick Questions */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                gap: 12,
                maxWidth: 600,
                margin: "0 auto",
              }}
            >
              {QUICK_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(q)}
                  style={{
                    padding: "12px 16px",
                    background: "rgba(51, 65, 85, 0.5)",
                    border: "1px solid #475569",
                    borderRadius: 12,
                    color: "#cbd5e1",
                    cursor: "pointer",
                    textAlign: "left",
                    fontSize: 14,
                    lineHeight: 1.4,
                    transition: "all 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.background = "rgba(59, 130, 246, 0.15)";
                    e.target.style.borderColor = "#3b82f6";
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = "rgba(51, 65, 85, 0.5)";
                    e.target.style.borderColor = "#475569";
                  }}
                >
                  {q}
                </button>
              ))}
            </div>

            <p
              style={{
                marginTop: 32,
                fontSize: 12,
                color: "#64748b",
                maxWidth: 500,
                margin: "32px auto 0",
              }}
            >
              ⚠️ This tool provides informational guidance only, not legal
              advice. Always consult a licensed immigration attorney for your
              specific situation.
            </p>
          </div>
        ) : (
          /* Chat Messages */
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent:
                    msg.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "85%",
                    padding: "14px 18px",
                    borderRadius: msg.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                    background:
                      msg.role === "user"
                        ? "linear-gradient(135deg, #3b82f6, #2563eb)"
                        : "rgba(51, 65, 85, 0.6)",
                    border:
                      msg.role === "assistant"
                        ? "1px solid #475569"
                        : "none",
                    lineHeight: 1.6,
                    fontSize: 15,
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {msg.content}

                  {/* Source badges for assistant messages */}
                  {msg.meta?.sources?.length > 0 && (
                    <div
                      style={{
                        marginTop: 12,
                        paddingTop: 8,
                        borderTop: "1px solid #475569",
                        display: "flex",
                        flexWrap: "wrap",
                        gap: 6,
                      }}
                    >
                      {msg.meta.sources.slice(0, 3).map((src, j) => (
                        <span
                          key={j}
                          style={{
                            fontSize: 11,
                            padding: "3px 8px",
                            background: "rgba(59, 130, 246, 0.15)",
                            borderRadius: 6,
                            color: "#93c5fd",
                          }}
                        >
                          📄 {src}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div
                  style={{
                    padding: "14px 18px",
                    borderRadius: "18px 18px 18px 4px",
                    background: "rgba(51, 65, 85, 0.6)",
                    border: "1px solid #475569",
                    color: "#94a3b8",
                  }}
                >
                  <span className="loading-dots">Researching</span>
                  <style jsx>{`
                    .loading-dots::after {
                      content: "";
                      animation: dots 1.5s steps(4, end) infinite;
                    }
                    @keyframes dots {
                      0%,
                      20% {
                        content: "";
                      }
                      40% {
                        content: ".";
                      }
                      60% {
                        content: "..";
                      }
                      80%,
                      100% {
                        content: "...";
                      }
                    }
                  `}</style>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Input Area */}
      <div
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          padding: "16px 16px 24px",
          background:
            "linear-gradient(transparent, rgba(15, 23, 42, 0.95) 30%)",
        }}
      >
        <div
          style={{
            maxWidth: 800,
            margin: "0 auto",
            display: "flex",
            gap: 10,
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about visas, green cards, documents, processing times..."
            rows={1}
            style={{
              flex: 1,
              padding: "14px 18px",
              borderRadius: 16,
              border: "1px solid #475569",
              background: "rgba(30, 41, 59, 0.8)",
              color: "#e2e8f0",
              fontSize: 15,
              resize: "none",
              outline: "none",
              fontFamily: "inherit",
            }}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            style={{
              padding: "14px 20px",
              borderRadius: 16,
              border: "none",
              background:
                input.trim() && !isLoading
                  ? "linear-gradient(135deg, #3b82f6, #2563eb)"
                  : "#334155",
              color: input.trim() && !isLoading ? "#fff" : "#64748b",
              cursor: input.trim() && !isLoading ? "pointer" : "not-allowed",
              fontSize: 15,
              fontWeight: 600,
              transition: "all 0.2s",
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
