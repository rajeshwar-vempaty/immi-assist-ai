import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  sendChatMessage,
  createChecklist,
  estimateTimeline,
  analyzeRFE,
  registerUser,
  getAuthMe,
  healthCheck,
  readinessCheck,
  setApiKey,
  getStoredApiKey,
} from "./api";

const BASE = "http://localhost:8000/api/v1";

/** Build a minimal fetch Response stand-in matching what apiRequest touches. */
function makeResponse({
  ok = true,
  status = 200,
  data = {},
  sessionId = null,
  jsonThrows = false,
} = {}) {
  return {
    ok,
    status,
    headers: {
      get: (name) => (name === "X-Session-ID" ? sessionId : null),
    },
    json: jsonThrows
      ? () => Promise.reject(new Error("invalid json"))
      : () => Promise.resolve(data),
  };
}

/** Parse the JSON body passed to the most recent fetch call. */
function lastBody() {
  const [, options] = global.fetch.mock.calls.at(-1);
  return options.body ? JSON.parse(options.body) : undefined;
}

function lastCall() {
  return global.fetch.mock.calls.at(-1);
}

beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue(makeResponse());
});

describe("request headers (getHeaders)", () => {
  it("always sends Content-Type application/json", async () => {
    await createChecklist({});
    const [, options] = lastCall();
    expect(options.headers["Content-Type"]).toBe("application/json");
  });

  it("injects X-API-Key and X-Session-ID from localStorage when present", async () => {
    localStorage.setItem("immi_api_key", "immi_abc");
    localStorage.setItem("immi_session_id", "sid-9");
    await createChecklist({});
    const [, options] = lastCall();
    expect(options.headers["X-API-Key"]).toBe("immi_abc");
    expect(options.headers["X-Session-ID"]).toBe("sid-9");
  });

  it("omits auth headers when localStorage is empty", async () => {
    await createChecklist({});
    const [, options] = lastCall();
    expect(options.headers).not.toHaveProperty("X-API-Key");
    expect(options.headers).not.toHaveProperty("X-Session-ID");
  });
});

describe("session persistence (saveSessionFromResponse)", () => {
  it("stores the X-Session-ID response header into localStorage", async () => {
    global.fetch.mockResolvedValue(makeResponse({ sessionId: "new-sid" }));
    await createChecklist({});
    expect(localStorage.getItem("immi_session_id")).toBe("new-sid");
  });

  it("leaves localStorage untouched when the response has no session header", async () => {
    global.fetch.mockResolvedValue(makeResponse({ sessionId: null }));
    await createChecklist({});
    expect(localStorage.getItem("immi_session_id")).toBeNull();
  });
});

describe("error handling (apiRequest)", () => {
  it("throws the server-provided error message on a non-ok JSON response", async () => {
    global.fetch.mockResolvedValue(
      makeResponse({ ok: false, status: 429, data: { error: "Rate limit exceeded" } })
    );
    await expect(createChecklist({})).rejects.toThrow("Rate limit exceeded");
  });

  it("falls back to a status-based message when the error body is not JSON", async () => {
    global.fetch.mockResolvedValue(
      makeResponse({ ok: false, status: 500, jsonThrows: true })
    );
    await expect(createChecklist({})).rejects.toThrow("API error: 500");
  });
});

describe("sendChatMessage", () => {
  it("POSTs to /chat, maps history to {role, content}, and omits session_id when absent", async () => {
    global.fetch.mockResolvedValue(
      makeResponse({ data: { response: "hi", session_id: "chat-1" } })
    );
    const history = [
      { role: "user", content: "a", extra: "drop-me" },
      { role: "assistant", content: "b" },
    ];
    const data = await sendChatMessage("hello", history);

    const [url, options] = lastCall();
    expect(url).toBe(`${BASE}/chat`);
    expect(options.method).toBe("POST");
    const body = lastBody();
    expect(body.message).toBe("hello");
    expect(body.chat_history).toEqual([
      { role: "user", content: "a" },
      { role: "assistant", content: "b" },
    ]);
    expect(body).not.toHaveProperty("session_id");
    expect(data.response).toBe("hi");
  });

  it("includes session_id in the body when provided", async () => {
    await sendChatMessage("hi", [], "sess-123");
    expect(lastBody().session_id).toBe("sess-123");
  });

  it("persists data.session_id to immi_chat_session_id", async () => {
    global.fetch.mockResolvedValue(
      makeResponse({ data: { response: "hi", session_id: "chat-99" } })
    );
    await sendChatMessage("hi", []);
    expect(localStorage.getItem("immi_chat_session_id")).toBe("chat-99");
  });
});

describe("feature endpoints route to the correct path and method", () => {
  it("createChecklist POSTs to /checklist", async () => {
    await createChecklist({ visa_type: "H1B" });
    const [url, options] = lastCall();
    expect(url).toBe(`${BASE}/checklist`);
    expect(options.method).toBe("POST");
    expect(lastBody()).toEqual({ visa_type: "H1B" });
  });

  it("estimateTimeline POSTs to /timeline", async () => {
    await estimateTimeline({ form_type: "I-129" });
    expect(lastCall()[0]).toBe(`${BASE}/timeline`);
    expect(lastCall()[1].method).toBe("POST");
  });

  it("analyzeRFE POSTs to /rfe/analyze", async () => {
    await analyzeRFE({ rfe_text: "text" });
    expect(lastCall()[0]).toBe(`${BASE}/rfe/analyze`);
    expect(lastCall()[1].method).toBe("POST");
  });

  it("registerUser defaults email to null and tier to starter", async () => {
    await registerUser();
    expect(lastCall()[0]).toBe(`${BASE}/auth/register`);
    expect(lastBody()).toEqual({ email: null, tier: "starter" });
  });

  it("registerUser passes through an explicit email and tier", async () => {
    await registerUser("a@b.com", "free");
    expect(lastBody()).toEqual({ email: "a@b.com", tier: "free" });
  });

  it("getAuthMe / healthCheck / readinessCheck issue GET requests to their paths", async () => {
    await getAuthMe();
    expect(lastCall()[0]).toBe(`${BASE}/auth/me`);
    expect(lastCall()[1].method).toBeUndefined();

    await healthCheck();
    expect(lastCall()[0]).toBe(`${BASE}/health`);

    await readinessCheck();
    expect(lastCall()[0]).toBe(`${BASE}/health/ready`);
  });
});

describe("API key storage helpers", () => {
  it("setApiKey stores a truthy key and getStoredApiKey reads it back", () => {
    setApiKey("immi_secret");
    expect(localStorage.getItem("immi_api_key")).toBe("immi_secret");
    expect(getStoredApiKey()).toBe("immi_secret");
  });

  it("setApiKey removes the key when given an empty value", () => {
    localStorage.setItem("immi_api_key", "immi_old");
    setApiKey("");
    expect(localStorage.getItem("immi_api_key")).toBeNull();
    expect(getStoredApiKey()).toBe("");
  });
});
