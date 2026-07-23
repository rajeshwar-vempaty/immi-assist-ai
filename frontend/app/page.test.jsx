import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// react-markdown is ESM-only and renders its string children; a passthrough
// keeps the assistant/RFE output assertable as plain text.
vi.mock("react-markdown", () => ({
  default: ({ children }) => children,
}));

// Mock the API client so handlers exercise component logic, not the network.
vi.mock("../lib/api", () => ({
  sendChatMessage: vi.fn(),
  createChecklist: vi.fn(),
  estimateTimeline: vi.fn(),
  analyzeRFE: vi.fn(),
  registerUser: vi.fn(),
  setApiKey: vi.fn(),
  getStoredApiKey: vi.fn(() => ""),
}));

import Home from "./page";
import * as api from "../lib/api";

const CHAT_PLACEHOLDER = "Ask an immigration question...";

beforeEach(() => {
  api.getStoredApiKey.mockReturnValue("");
});

describe("initial render", () => {
  it("shows the header, tabs, and chat empty-state quick questions", () => {
    render(<Home />);
    expect(screen.getByText("ImmiAssist AI")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Checklist" })).toBeInTheDocument();
    expect(screen.getByText("Immigration Q&A")).toBeInTheDocument();
    expect(
      screen.getByText("How do I transfer my H-1B to a new employer?")
    ).toBeInTheDocument();
  });

  it("hydrates the API key input from storage on mount", () => {
    api.getStoredApiKey.mockReturnValue("immi_stored");
    render(<Home />);
    expect(api.getStoredApiKey).toHaveBeenCalled();
    expect(screen.getByPlaceholderText("API Key (optional)")).toHaveValue("immi_stored");
  });
});

describe("tab navigation", () => {
  it("switches to the checklist tab when its nav button is clicked", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Checklist" }));
    expect(screen.getByText("Document Checklist")).toBeInTheDocument();
  });
});

describe("chat (handleSend)", () => {
  it("sends the typed message and renders the assistant reply with sources", async () => {
    api.sendChatMessage.mockResolvedValue({
      response: "Here is guidance.",
      intent: "POLICY_QA",
      model_used: "claude",
      sources: ["USCIS Policy Manual", "8 CFR 214.2", "Form I-129 Instructions", "extra"],
    });
    const user = userEvent.setup();
    render(<Home />);

    await user.type(screen.getByPlaceholderText(CHAT_PLACEHOLDER), "How do I renew?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(api.sendChatMessage).toHaveBeenCalledWith("How do I renew?", [], null)
    );
    expect(screen.getByText("How do I renew?")).toBeInTheDocument();
    expect(await screen.findByText("Here is guidance.")).toBeInTheDocument();
    // sources are sliced to the first three
    expect(screen.getByText("📄 USCIS Policy Manual")).toBeInTheDocument();
    expect(screen.queryByText("📄 extra")).not.toBeInTheDocument();
  });

  it("ignores an empty/whitespace message", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(api.sendChatMessage).not.toHaveBeenCalled();
  });

  it("sends a quick question when its button is clicked", async () => {
    api.sendChatMessage.mockResolvedValue({ response: "ok", sources: [] });
    const user = userEvent.setup();
    render(<Home />);
    await user.click(
      screen.getByText("What is the EB-2 NIW process?")
    );
    await waitFor(() =>
      expect(api.sendChatMessage).toHaveBeenCalledWith(
        "What is the EB-2 NIW process?",
        [],
        null
      )
    );
  });

  it("surfaces the error message in a banner when the request fails", async () => {
    api.sendChatMessage.mockRejectedValue(new Error("Service unavailable"));
    const user = userEvent.setup();
    render(<Home />);
    await user.type(screen.getByPlaceholderText(CHAT_PLACEHOLDER), "hello");
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Service unavailable")).toBeInTheDocument();
  });

  it("submits on Enter key", async () => {
    api.sendChatMessage.mockResolvedValue({ response: "pong", sources: [] });
    const user = userEvent.setup();
    render(<Home />);
    await user.type(screen.getByPlaceholderText(CHAT_PLACEHOLDER), "ping{Enter}");
    await waitFor(() =>
      expect(api.sendChatMessage).toHaveBeenCalledWith("ping", [], null)
    );
  });
});

describe("checklist (handleChecklist)", () => {
  it("calls createChecklist with the selected visa type and renders the result", async () => {
    api.createChecklist.mockResolvedValue({
      visa_type: "H1B",
      form_number: "I-129",
      filing_fee: "$460",
      estimated_prep_time: "2 weeks",
      checklist: [
        {
          category: "Forms",
          items: [{ required: true, document: "Form I-129", description: "the petition" }],
        },
      ],
      disclaimer: "Not legal advice",
    });
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Checklist" }));
    await user.click(screen.getByRole("button", { name: "Generate Checklist" }));

    await waitFor(() =>
      expect(api.createChecklist).toHaveBeenCalledWith({ visa_type: "H1B", details: "" })
    );
    expect(await screen.findByText("H1B — I-129")).toBeInTheDocument();
    expect(screen.getByText(/the petition/)).toBeInTheDocument();
  });
});

describe("timeline (handleTimeline)", () => {
  it("calls estimateTimeline with a null filing date when none is entered", async () => {
    api.estimateTimeline.mockResolvedValue({
      form_type: "I-129",
      case_status: "NORMAL",
      status_explanation: "On track",
      processing_range_months: { min: 3, max: 6 },
      disclaimer: "Estimates only",
    });
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Timeline" }));
    await user.click(screen.getByRole("button", { name: "Estimate Timeline" }));

    await waitFor(() =>
      expect(api.estimateTimeline).toHaveBeenCalledWith({
        form_type: "I-129",
        service_center: "California Service Center",
        filing_date: null,
      })
    );
    expect(await screen.findByText("On track")).toBeInTheDocument();
  });
});

describe("RFE (handleRFE)", () => {
  it("keeps the analyze button disabled until the text reaches 10 characters", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Rfe" }));

    const analyze = screen.getByRole("button", { name: "Analyze RFE" });
    expect(analyze).toBeDisabled();

    await user.type(
      screen.getByPlaceholderText("Paste your RFE notice text here..."),
      "too short"
    );
    expect(analyze).toBeDisabled();
    expect(api.analyzeRFE).not.toHaveBeenCalled();
  });

  it("analyzes the RFE once the text is long enough and renders the result", async () => {
    api.analyzeRFE.mockResolvedValue({
      summary: "Summary text",
      risk_level: "high",
      deadline_info: "30 days",
      points: [{ issue: "Missing wage evidence", evidence_suggestions: ["Pay stubs"] }],
      disclaimer: "Not legal advice",
    });
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Rfe" }));

    const rfeText = "This RFE requests additional wage-level evidence for the petition.";
    await user.type(
      screen.getByPlaceholderText("Paste your RFE notice text here..."),
      rfeText
    );
    await user.click(screen.getByRole("button", { name: "Analyze RFE" }));

    await waitFor(() =>
      expect(api.analyzeRFE).toHaveBeenCalledWith({ rfe_text: rfeText })
    );
    expect(await screen.findByText("high")).toBeInTheDocument();
    expect(screen.getByText("Missing wage evidence")).toBeInTheDocument();
    expect(screen.getByText("Pay stubs")).toBeInTheDocument();
  });
});

describe("API key controls", () => {
  it("saves the entered API key via setApiKey", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await user.type(screen.getByPlaceholderText("API Key (optional)"), "immi_secret");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(api.setApiKey).toHaveBeenCalledWith("immi_secret");
  });

  it("registers a free-tier key and stores it on success", async () => {
    api.registerUser.mockResolvedValue({
      api_key: "immi_new",
      tier: "free",
      daily_limit: 20,
    });
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Get Key" }));

    await waitFor(() => expect(api.registerUser).toHaveBeenCalledWith(null, "free"));
    expect(api.setApiKey).toHaveBeenCalledWith("immi_new");
    expect(window.alert).toHaveBeenCalled();
    expect(screen.getByPlaceholderText("API Key (optional)")).toHaveValue("immi_new");
  });

  it("shows an error banner when registration is rejected", async () => {
    api.registerUser.mockRejectedValue(new Error("Registration disabled"));
    const user = userEvent.setup();
    render(<Home />);
    await user.click(screen.getByRole("button", { name: "Get Key" }));
    expect(await screen.findByText("Registration disabled")).toBeInTheDocument();
  });
});
