"use client";

import { useEffect, useState } from "react";

const THINKING_LINES = [
  { icon: "passport", text: "Checking the imaginary USCIS waiting room…" },
  { icon: "docs", text: "Counting forms so you don’t have to…" },
  { icon: "compass", text: "Plotting a calmer path through the paperwork…" },
  { icon: "bag", text: "Packing citations into a neat little suitcase…" },
  { icon: "mug", text: "Brewing clarity (still hotter than a NOID)…" },
  { icon: "search", text: "Skimming policy manuals at polite robot speed…" },
  { icon: "map", text: "Tracing timelines without promising miracles…" },
  { icon: "clip", text: "Stapling useful bits together…" },
  { icon: "plane", text: "Taxiing toward an answer…" },
  { icon: "clock", text: "Processing… unlike your case, this one is quick." },
];

function ThinkingIcon({ name }) {
  const common = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none",
    "aria-hidden": true,
  };
  switch (name) {
    case "passport":
      return (
        <svg {...common}>
          <rect x="5" y="3" width="14" height="18" rx="2" stroke="currentColor" strokeWidth="1.7" />
          <circle cx="12" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.7" />
          <path d="M8 16h8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      );
    case "docs":
      return (
        <svg {...common}>
          <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.7" />
          <path d="M14 3v5h5M9 13h6M9 17h4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      );
    case "compass":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.7" />
          <path d="m14.8 9.2-1.7 5.1-5.1 1.7 1.7-5.1 5.1-1.7Z" stroke="currentColor" strokeWidth="1.5" fill="rgba(31,111,106,0.2)" />
        </svg>
      );
    case "bag":
      return (
        <svg {...common}>
          <path d="M6 8h12l-1 12H7L6 8Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M9 8V6.5A3 3 0 0 1 12 3.5 3 3 0 0 1 15 6.5V8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      );
    case "mug":
      return (
        <svg {...common}>
          <path d="M6 7h10v8a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V7Z" stroke="currentColor" strokeWidth="1.7" />
          <path d="M16 9h2.5a2.5 2.5 0 0 1 0 5H16" stroke="currentColor" strokeWidth="1.7" />
          <path d="M8 4c.6.8.6 1.7 0 2.5M11 4c.6.8.6 1.7 0 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "map":
      return (
        <svg {...common}>
          <path d="m3 7 6-2 6 2 6-2v14l-6 2-6-2-6 2V7Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M9 5v14M15 7v14" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      );
    case "clip":
      return (
        <svg {...common}>
          <path d="M15.5 7.5 9 14a2.5 2.5 0 1 0 3.5 3.5l7-7a4 4 0 0 0-5.7-5.7l-7.5 7.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "plane":
      return (
        <svg {...common}>
          <path d="M3 12h18M14 6l7 6-7 6M10 8 3 12l7 4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "clock":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.7" />
          <path d="M12 8v5l3 2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <circle cx="11" cy="11" r="6" stroke="currentColor" strokeWidth="1.7" />
          <path d="m16 16 3.5 3.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      );
  }
}

export default function ChatThinking() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * THINKING_LINES.length));

  useEffect(() => {
    const id = setInterval(() => {
      setIndex((prev) => {
        let next = prev;
        while (next === prev) next = Math.floor(Math.random() * THINKING_LINES.length);
        return next;
      });
    }, 2200);
    return () => clearInterval(id);
  }, []);

  const line = THINKING_LINES[index];

  return (
    <div className="bubble assistant thinking-bubble" aria-live="polite">
      <div className="thinking-row">
        <span className="thinking-icon">
          <ThinkingIcon name={line.icon} />
        </span>
        <div className="thinking-copy">
          <div className="thinking-label">Working on it</div>
          <div className="thinking-text">{line.text}</div>
        </div>
        <span className="thinking-dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
      </div>
    </div>
  );
}
