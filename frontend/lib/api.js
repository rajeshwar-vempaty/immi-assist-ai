/**
 * API client — session JWT via cookie + Authorization header.
 * Provider API keys are NEVER stored in the browser.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const TOKEN_KEY = "immi_access_token";

export function getAccessToken() {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(TOKEN_KEY) || "";
}

export function setAccessToken(token) {
  if (typeof window === "undefined") return;
  if (token) sessionStorage.setItem(TOKEN_KEY, token);
  else sessionStorage.removeItem(TOKEN_KEY);
}

export function clearClientSession() {
  if (typeof window === "undefined") return;
  const keys = [];
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k && k.startsWith("immi_")) keys.push(k);
  }
  keys.forEach((k) => localStorage.removeItem(k));
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem("immi_draft_message");
}

function getHeaders(extra = {}) {
  const headers = { "Content-Type": "application/json", ...extra };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async def apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: getHeaders(options.headers || {}),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    let message = err.error || `API error: ${response.status}`;
    if (!err.error && err.detail) {
      if (typeof err.detail === "string") message = err.detail;
      else if (Array.isArray(err.detail)) {
        message = err.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
      }
    }
    const error = new Error(message);
    error.status = response.status;
    error.payload = err;
    throw error;
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function getAuthConfig() {
  return apiRequest("/auth/config");
}

export async function loginWithGoogle(idToken) {
  const data = await apiRequest("/auth/google", {
    method: "POST",
    body: JSON.stringify({ id_token: idToken }),
  });
  setAccessToken(data.access_token);
  return data;
}

export async function loginDev(email, name) {
  const data = await apiRequest("/auth/dev-login", {
    method: "POST",
    body: JSON.stringify({ email, name }),
  });
  setAccessToken(data.access_token);
  return data;
}

export async function logout() {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } finally {
    clearClientSession();
  }
}

export async function getAuthMe() {
  return apiRequest("/auth/me");
}

export async function sendChatMessage({
  message,
  chatHistory = [],
  conversationId = null,
  provider = null,
  model = null,
}) {
  return apiRequest("/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      chat_history: chatHistory.map((msg) => ({
        role: msg.role,
        content: msg.content,
      })),
      conversation_id: conversationId,
      provider,
      model,
    }),
  });
}

export async function listConversations() {
  return apiRequest("/conversations");
}

export async function getConversation(id) {
  return apiRequest(`/conversations/${id}`);
}

export async function createConversation(title = "New conversation") {
  return apiRequest("/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(id) {
  return apiRequest(`/conversations/${id}`, { method: "DELETE" });
}

export async function createChecklist(payload) {
  return apiRequest("/checklist", { method: "POST", body: JSON.stringify(payload) });
}

export async function estimateTimeline(payload) {
  return apiRequest("/timeline", { method: "POST", body: JSON.stringify(payload) });
}

export async function analyzeRFE(payload) {
  return apiRequest("/rfe/analyze", { method: "POST", body: JSON.stringify(payload) });
}

export async function getSettingsPreferences() {
  return apiRequest("/settings/preferences");
}

export async function updateSettingsPreferences(payload) {
  return apiRequest("/settings/preferences", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function listCredentials() {
  return apiRequest("/settings/credentials");
}

export async function saveCredential(provider, apiKey) {
  return apiRequest(`/settings/credentials/${provider}`, {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export async function testCredential(provider, apiKey = null) {
  return apiRequest(`/settings/credentials/${provider}/test`, {
    method: "POST",
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export async function deleteCredential(provider) {
  return apiRequest(`/settings/credentials/${provider}`, { method: "DELETE" });
}
