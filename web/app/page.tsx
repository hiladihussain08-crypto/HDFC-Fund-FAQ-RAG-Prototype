"use client";

import { useEffect, useRef, useState } from "react";
import { Shield, Send, RotateCcw, Sun, Moon } from "lucide-react";

type Hero = { label: string; value: string; context: string | null };
type Chunk = { text: string; source: string };
type Meta = { mode: string; latency_ms: number; query_id: string; chunks: Chunk[] };
type ApiResponse = {
  status: "factual" | "refused" | "not_found" | "error";
  answer: string;
  hero: Hero | null;
  fund_name: string | null;
  intent: string | null;
  source_url: string | null;
  last_updated: string | null;
  meta: Meta;
};

type Message =
  | { id: string; role: "user"; content: string }
  | { id: string; role: "assistant"; response: ApiResponse }
  | { id: string; role: "assistant"; error: string; retry: string };

const CORE = ["Expense ratio", "Exit load", "Minimum SIP"] as const;
const FOLLOWUPS: Record<string, string[]> = {
  expense_ratio: ["Exit load", "Minimum SIP"],
  exit_load: ["Expense ratio", "Minimum SIP"],
  min_sip: ["Expense ratio", "Exit load"],
};
const CHIP_TOPIC: Record<string, string> = {
  "Expense ratio": "expense ratio",
  "Exit load": "exit load",
  "Minimum SIP": "minimum SIP",
};

const STARTERS = ["Expense ratio", "Exit load", "Minimum SIP"];
const STARTER_QUESTIONS: Record<string, string> = {
  "Expense ratio": "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
  "Exit load": "What is the exit load of HDFC Large Cap Fund Direct Growth?",
  "Minimum SIP": "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
};

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function formatUpdated(s: string | null) {
  if (!s) return "";
  const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return s;
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `Updated ${parseInt(m[3])} ${months[parseInt(m[2]) - 1]} ${m[1]}`;
}

function domainOf(url: string) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [emptyError, setEmptyError] = useState<string | null>(null);
  const [fading, setFading] = useState(false);
  const [slow, setSlow] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const started = messages.length > 0;

  // read theme from localStorage after mount
  useEffect(() => {
    try {
      const t = localStorage.getItem("theme");
      if (t === "light" || t === "dark") setTheme(t);
    } catch {
      /* ignore */
    }
  }, []);

  // sync theme to document
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    try {
      localStorage.setItem("theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loading) {
      setSlow(false);
      return;
    }
    const t = setTimeout(() => setSlow(true), 5000);
    return () => clearTimeout(t);
  }, [loading]);

  async function sendQuestion(question: string) {
    const q = question.trim();
    if (!q) {
      setEmptyError("Enter a question first");
      return;
    }
    setEmptyError(null);
    setFading(true);
    const userMsg: Message = { id: uid(), role: "user", content: q };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = (data && (data.error || data.detail)) || "Something went wrong. Please try again.";
        setMessages((m) => [...m, { id: uid(), role: "assistant", error: String(msg), retry: q }]);
      } else {
        setMessages((m) => [...m, { id: uid(), role: "assistant", response: data as ApiResponse }]);
      }
    } catch {
      setMessages((m) => [...m, { id: uid(), role: "assistant", error: "Could not reach the server. Please try again.", retry: q }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion(input);
    }
  }

  const lastAssistantIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return i;
    }
    return -1;
  })();

  const toggleTheme = () => setTheme((t) => (t === "light" ? "dark" : "light"));

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden">
      {/* Header */}
      <header className="flex h-16 shrink-0 items-center justify-between gap-3 px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--ink)] text-sm font-semibold text-[var(--on-ink)]">
            F
          </div>
          <span className="text-lg font-semibold text-[var(--text)]">Fund FAQ assistant</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-2)]">
            <Shield className="h-3.5 w-3.5" />
            <span className="hidden min-[480px]:inline">Facts only, no advice</span>
          </span>
          <button
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="toggle-btn"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="relative flex min-h-0 flex-1 flex-col">
        {/* glow moved into dock */}

        {!started ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 px-5 text-center">
            <div className={`sphere ${fading ? "fade" : ""}`} />
            <h2 className="font-outfit text-[28px] font-light leading-tight text-[var(--text)] sm:text-[22px]">
              Ask about any mutual fund
            </h2>
            <p className="text-[13px] text-[var(--text-2)]">Factual answers from official fund pages, with one citation per answer.</p>
            <p className="text-[12px] text-[var(--text-2)]">Covers selected HDFC schemes</p>
          </div>
        ) : (
          <div className="mask-fade flex-1 overflow-y-auto px-5 py-6 scrollbar-thin">
            <div className="mx-auto flex max-w-[760px] flex-col gap-5" aria-live="polite">
              {messages.map((m, i) => {
                if (m.role === "user") {
                  return (
                    <div key={m.id} className="flex justify-end">
                      <div className="bubble-user">{m.content}</div>
                    </div>
                  );
                }
                if ("error" in m) {
                  return (
                    <div key={m.id} className="flex items-start gap-2.5">
                      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--ink)] text-xs font-semibold text-[var(--on-ink)]">
                        F
                      </div>
                      <div className="max-w-[85%]">
                        <span className="status-chip status-error mb-2">
                          <span className="dot" /> Something went wrong
                        </span>
                        <div className="card">
                          <p className="text-[15px] leading-relaxed text-[var(--text)]">{m.error}</p>
                        </div>
                        <button
                          onClick={() => sendQuestion(m.retry)}
                          className="mt-2 inline-flex items-center gap-1 rounded-full border border-[rgba(17,17,17,0.14)] bg-[var(--chip-fill)] px-3 py-1.5 text-xs text-[var(--text)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
                        >
                          <RotateCcw className="h-3 w-3" /> Try again
                        </button>
                      </div>
                    </div>
                  );
                }
                const r = m.response;
                const status =
                  r.status === "factual"
                    ? { cls: "status-factual", label: "Factual answer" }
                    : r.status === "refused"
                    ? { cls: "status-refused", label: "I can't advise on that" }
                    : r.status === "not_found"
                    ? { cls: "status-notfound", label: "Not in my data" }
                    : { cls: "status-error", label: "Something went wrong" };

                const isLast = i === lastAssistantIndex;
                const chips =
                  r.status === "factual" && r.intent
                    ? (FOLLOWUPS[r.intent] || []).slice(0, 3)
                    : [];
                const fundName = r.fund_name;

                return (
                  <div key={m.id} className="flex items-start gap-2.5 fade-in">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--ink)] text-xs font-semibold text-[var(--on-ink)]">
                      F
                    </div>
                    <div className="max-w-[85%]">
                      <span className={`status-chip ${status.cls} mb-2`}>
                        <span className="dot" /> {status.label}
                      </span>
                      <div className="card">
                        {r.hero ? (
                          <div className="flex flex-col gap-1">
                            <div className="hero-label">{r.hero.label}</div>
                            <div className="flex items-baseline gap-3">
                              <span className="hero-value">{r.hero.value}</span>
                              {r.hero.context && <span className="hero-context">{r.hero.context}</span>}
                            </div>
                          </div>
                        ) : (
                          <p className="text-[15px] leading-relaxed text-[var(--text)]">{r.answer}</p>
                        )}
                      </div>
                      {r.status === "factual" && r.source_url && (
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--text-2)]">
                          <a href={r.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
                            {domainOf(r.source_url)}
                          </a>
                          <span className="inline-flex items-center gap-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                            {formatUpdated(r.last_updated)}
                          </span>
                          <details className="details-panel ml-auto">
                            <summary>How this was answered</summary>
                            <div className="mt-2 space-y-1">
                              <div>Mode: {r.meta.mode}</div>
                              <div>Intent: {r.intent || "—"}</div>
                              <div>Latency: {r.meta.latency_ms} ms</div>
                              <div>Query ID: {r.meta.query_id}</div>
                              {r.meta.chunks && r.meta.chunks.length > 0 && (
                                <div className="mt-2">
                                  <div className="font-semibold">Retrieved chunks</div>
                                  {r.meta.chunks.slice(0, 5).map((c, j) => (
                                    <div key={j} className="mt-1">
                                      <div className="text-[var(--text-2)]">{c.source}</div>
                                      <div>{c.text.slice(0, 300)}</div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </details>
                        </div>
                      )}
                      {isLast && chips.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {chips.map((chip) => (
                            <button
                              key={chip}
                              onClick={() => sendQuestion(`What is the ${CHIP_TOPIC[chip].toLowerCase()} of ${fundName || "HDFC Large Cap Fund Direct Growth"}?`)}
                              className="chip"
                            >
                              {chip}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              {loading && (
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--ink)] text-xs font-semibold text-[var(--on-ink)]">
                    F
                  </div>
                  <div className="rounded-[20px] border border-[rgba(17,17,17,0.10)] bg-white/55 p-4 backdrop-blur-md">
                    {slow ? (
                      <p className="text-[13px] text-[#6b665f]">Waking up the assistant, the first answer can take up to a minute.</p>
                    ) : (
                      <div className="typing flex gap-1">
                        <span /><span /><span />
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>
        )}

        {/* Dock */}
        <div className="relative shrink-0 px-5 py-3">
          <div
            className={`pointer-events-none absolute left-1/2 top-1/2 z-0 h-[170px] w-[min(640px,100vw)] -translate-x-1/2 -translate-y-1/2 ${started ? "opacity-60" : fading ? "opacity-0" : "opacity-100"}`}
            style={{ background: "radial-gradient(ellipse at center, rgba(255,122,26,var(--glow-alpha)), rgba(255,122,26,0) 70%)", filter: "blur(20px)", transition: "opacity 500ms" }}
            aria-hidden
          />
          <div className="relative z-10 mx-auto flex max-w-[720px] flex-col gap-2">
            {!started && (
              <div className="flex flex-wrap justify-center gap-2">
                {STARTERS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendQuestion(STARTER_QUESTIONS[s])}
                    className="chip"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            <div className="composer">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  if (e.target.value.trim().length > 0 && !fading) setFading(true);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Ask about expense ratio, exit load, SIP…"
                maxLength={300}
                className="flex-1 bg-transparent text-[15px] text-[var(--text)] outline-none placeholder:text-[var(--text-2)]"
              />
              <button
                onClick={() => sendQuestion(input)}
                disabled={loading || input.trim().length === 0}
                aria-label="Send"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            {emptyError && <div className="text-center text-xs text-[#d92d20]">{emptyError}</div>}
            <div className="caption">Facts from public fund pages. Not investment advice.</div>
          </div>
        </div>
      </main>
    </div>
  );
}
