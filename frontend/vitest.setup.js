import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom does not implement scrollIntoView; page.js calls it in a mount effect.
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// jsdom does not implement alert; handleRegister uses it on success.
window.alert = vi.fn();

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
