/**
 * API client for ImmiAssist backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (typeof window !== "undefined") {
    const apiKey = localStorage.getItem("immi_api_key");
    const sessionId = localStorage.getItem("immi_session_id");
    if (apiKey) headers["X-API-Key"] = apiKey;
    if (sessionId) headers["X-Session-ID"] = sessionId;
  }
  return headers;
}

function saveSessionFromResponse(response) {
  const sessionId = response.headers.get("X-Session-ID");
  if (sessionId && typeof window !== "undefined") {
    localStorage.setItem("immi_session_id", sessionId);
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...getHeaders(), ...options.headers },
  });
  saveSessionFromResponse(response);
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error || `API error: ${response.status}`);
  }
  return response.json();
}

export async function sendChatMessage(message, chatHistory = [], sessionId = null) {
  const body = {
    message,
    chat_history: chatHistory.map((msg) => ({
      role: msg.role,
      content: msg.content,
    })),
  };
  if (sessionId) body.session_id = sessionId;

  const data = await apiRequest("/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (data.session_id && typeof window !== "undefined") {
    localStorage.setItem("immi_chat_session_id", data.session_id);
  }
  return data;
}

export async function createChecklist(payload) {
  return apiRequest("/checklist", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function estimateTimeline(payload) {
  return apiRequest("/timeline", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function analyzeRFE(payload) {
  return apiRequest("/rfe/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function registerUser(email = null, tier = "starter") {
  return apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, tier }),
  });
}

export async function getAuthMe() {
  return apiRequest("/auth/me");
}

export async function healthCheck() {
  return apiRequest("/health");
}

export async function readinessCheck() {
  return apiRequest("/health/ready");
}

export function setApiKey(key) {
  if (typeof window !== "undefined") {
    if (key) localStorage.setItem("immi_api_key", key);
    else localStorage.removeItem("immi_api_key");
  }
}

export function getStoredApiKey() {
  if (typeof window !== "undefined") {
    return localStorage.getItem("immi_api_key") || "";
  }
  return "";
}
