"use client";

import { useEffect, useRef, useState } from "react";
import { Shield, Send, RotateCcw } from "lucide-react";

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

const FOLLOWUPS: Record<string, string[]> = {
  expense_ratio: ["Exit load", "Minimum SIP", "Fund manager"],
  exit_load: ["Expense ratio", "Minimum SIP", "Fund manager"],
  min_sip: ["Expense ratio", "Exit load", "Fund manager"],
  min_investment: ["Expense ratio", "Exit load", "Minimum SIP"],
  fund_manager: ["Expense ratio", "Exit load", "Minimum SIP"],
  fund_house: ["Expense ratio", "Exit load", "Minimum SIP"],
  aum: ["Expense ratio", "Exit load", "Minimum SIP"],
  category: ["Expense ratio", "Exit load", "Minimum SIP"],
  lock_in: ["Expense ratio", "Exit load", "Minimum SIP"],
  riskometer: ["Expense ratio", "Exit load", "Minimum SIP"],
  benchmark: ["Expense ratio", "Exit load", "Minimum SIP"],
  launch_date: ["Expense ratio", "Exit load", "Minimum SIP"],
  stamp_duty: ["Expense ratio", "Exit load", "Minimum SIP"],
};

const CHIP_TOPIC: Record<string, string> = {
  "Expense ratio": "expense ratio",
  "Exit load": "exit load",
  "Minimum SIP": "minimum SIP",
  "Fund manager": "fund manager",
};

const STARTERS = ["Expense ratio", "Exit load", "Minimum SIP", "Fund manager"];
const STARTER_QUESTIONS: Record<string, string> = {
  "Expense ratio": "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
  "Exit load": "What is the exit load of HDFC Large Cap Fund Direct Growth?",
  "Minimum SIP": "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
  "Fund manager": "Who is the fund manager of HDFC Large Cap Fund Direct Growth?",
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
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const started = messages.length > 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

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

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden">
      {/* Header */}
      <header className="flex h-16 shrink-0 items-center justify-between gap-3 px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#111111] text-sm font-semibold text-white">
            F
          </div>
          <span className="text-lg font-semibold text-[#111111]">Fund FAQ assistant</span>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(17,17,17,0.10)] bg-white/55 px-3 py-1.5 text-xs text-[#111111] backdrop-blur-md">
          <Shield className="h-3.5 w-3.5 text-[#111111]" />
          Facts only, no advice
        </span>
      </header>

      {/* Main */}
      <main className="relative flex min-h-0 flex-1 flex-col">
        {/* glow */}
        <div
          className={`pointer-events-none absolute bottom-0 left-1/2 z-0 h-40 w-[520px] -translate-x-1/2 ${started ? "opacity-10" : fading ? "opacity-0" : "opacity-[0.18]"}`}
          style={{ background: "radial-gradient(ellipse at center, rgba(255,122,26,0.18), transparent 70%)", transition: "opacity 500ms" }}
        />

        {!started ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 px-5 text-center">
            <div className={`sphere ${fading ? "fade" : ""}`} />
            <h2 className="font-outfit text-[28px] font-light leading-tight text-[#111111] sm:text-[22px]">
              Ask about any mutual fund
            </h2>
            <p className="text-[13px] text-[#6b665f]">Factual answers from official fund pages, with one citation per answer.</p>
          </div>
        ) : (
          <div className="mask-fade flex-1 overflow-y-auto px-5 py-6">
            <div className="mx-auto flex max-w-[760px] flex-col gap-5" aria-live="polite">
              {messages.map((m, i) => {
                if (m.role === "user") {
                  return (
                    <div key={m.id} className="flex justify-end">
                      <div className="max-w-[75%] rounded-[18px_18px_4px_18px] bg-[#111111] px-3.5 py-2.5 text-[15px] leading-relaxed text-white break-words whitespace-pre-wrap">
                        {m.content}
                      </div>
                    </div>
                  );
                }
                if ("error" in m) {
                  return (
                    <div key={m.id} className="flex items-start gap-2.5">
                      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#111111] text-xs font-semibold text-white">
                        F
                      </div>
                      <div className="max-w-[85%]">
                        <span className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-[#d92d20] bg-[#fdecea] px-2.5 py-1 text-xs font-medium text-[#d92d20]">
                          <span className="h-1.5 w-1.5 rounded-full bg-[#d92d20]" />
                          Something went wrong
                        </span>
                        <div className="rounded-[20px] border border-[rgba(17,17,17,0.10)] bg-white/55 p-4 backdrop-blur-md">
                          <p className="text-[15px] leading-relaxed text-[#111111]">{m.error}</p>
                        </div>
                        <button
                          onClick={() => sendQuestion(m.retry)}
                          className="mt-2 inline-flex items-center gap-1 rounded-full border border-[rgba(17,17,17,0.14)] bg-white px-3 py-1.5 text-xs text-[#111111] transition hover:border-[#c23e08] hover:text-[#c23e08]"
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
                    ? { cls: "bg-[#e6f6f0] text-[#111111] border-[#111111]", label: "Factual answer", dot: "#111111" }
                    : r.status === "refused"
                    ? { cls: "bg-[#fef3e2] text-[#e8890c] border-[#e8890c]", label: "I can't advise on that", dot: "#e8890c" }
                    : r.status === "not_found"
                    ? { cls: "bg-[#eef1f5] text-[#6b7a90] border-[#6b7a90]", label: "Not in my data", dot: "#6b7a90" }
                    : { cls: "bg-[#fdecea] text-[#d92d20] border-[#d92d20]", label: "Something went wrong", dot: "#d92d20" };

                const isLast = i === lastAssistantIndex;
                const chips = r.status === "factual" && r.intent ? (FOLLOWUPS[r.intent] || []).slice(0, 3) : [];
                const fundName = r.fund_name;

                return (
                  <div key={m.id} className="flex items-start gap-2.5 fade-in">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#111111] text-xs font-semibold text-white">
                      F
                    </div>
                    <div className="max-w-[85%]">
                      <span className={`mb-2 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${status.cls}`}>
                        <span className="h-1.5 w-1.5 rounded-full" style={{ background: status.dot }} />
                        {status.label}
                      </span>
                      <div className="rounded-[20px] border border-[rgba(17,17,17,0.10)] bg-white/55 p-4 backdrop-blur-md">
                        {r.hero ? (
                          <div className="mb-1 flex flex-col gap-1">
                            <div className="text-xs text-[#6b665f]">{r.hero.label}</div>
                            <div className="flex items-baseline gap-3">
                              <span className="font-outfit text-[34px] font-light leading-none text-[#111111]">{r.hero.value}</span>
                              {r.hero.context && <span className="text-[13px] text-[#6b665f]">{r.hero.context}</span>}
                            </div>
                          </div>
                        ) : (
                          <p className="text-[15px] leading-relaxed text-[#111111]">{r.answer}</p>
                        )}
                      </div>
                      {r.status === "factual" && r.source_url && (
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[#6b665f]">
                          <a href={r.source_url} target="_blank" rel="noopener noreferrer" className="rounded-full border border-[rgba(17,17,17,0.10)] bg-white px-2 py-0.5 font-medium text-[#c23e08] underline-offset-2 hover:underline">
                            {domainOf(r.source_url)}
                          </a>
                          <span className="inline-flex items-center gap-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                            {formatUpdated(r.last_updated)}
                          </span>
                          <details className="ml-auto">
                            <summary className="cursor-pointer text-[#6b665f] hover:text-[#c23e08]">How this was answered</summary>
                            <div className="mt-2 rounded-lg border border-[rgba(17,17,17,0.10)] bg-white/80 p-3 text-xs">
                              <div>Mode: {r.meta.mode}</div>
                              <div>Intent: {r.intent || "—"}</div>
                              <div>Latency: {r.meta.latency_ms} ms</div>
                              <div>Query ID: {r.meta.query_id}</div>
                              {r.meta.chunks && r.meta.chunks.length > 0 && (
                                <div className="mt-2">
                                  <div className="font-semibold">Retrieved chunks</div>
                                  {r.meta.chunks.slice(0, 5).map((c, j) => (
                                    <div key={j} className="mt-1">
                                      <div className="text-[#6b665f]">{c.source}</div>
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
                              className="rounded-full border border-[rgba(17,17,17,0.14)] bg-white px-3.5 py-1.5 text-[13px] text-[#111111] transition hover:border-[#c23e08] hover:text-[#c23e08]"
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
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#111111] text-xs font-semibold text-white">
                    F
                  </div>
                  <div className="rounded-[20px] border border-[rgba(17,17,17,0.10)] bg-white/55 p-4 backdrop-blur-md">
                    <div className="typing flex gap-1">
                      <span /><span /><span />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>
        )}

        {/* Dock */}
        <div className="shrink-0 px-5 py-3 backdrop-blur-md">
          <div className="mx-auto flex max-w-[720px] flex-col gap-2">
            {!started && (
              <div className="flex flex-wrap justify-center gap-2">
                {STARTERS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendQuestion(STARTER_QUESTIONS[s])}
                    className="rounded-full border border-[rgba(17,17,17,0.14)] bg-white px-3.5 py-1.5 text-[13px] text-[#111111] transition hover:border-[#c23e08] hover:text-[#c23e08]"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2">
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
                className="h-14 flex-1 rounded-full border border-[rgba(17,17,17,0.10)] bg-white/55 px-5 text-[15px] text-[#111111] outline-none backdrop-blur-md transition focus:border-[#c23e08]"
              />
              <button
                onClick={() => sendQuestion(input)}
                disabled={loading || input.trim().length === 0}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#111111] text-white transition hover:bg-[#c23e08] disabled:opacity-40"
                aria-label="Send"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            {emptyError && <div className="text-center text-xs text-[#d92d20]">{emptyError}</div>}
            <div className="text-center text-[11px] text-[#6b665f]">Facts from public fund pages. Not investment advice.</div>
          </div>
        </div>
      </main>
    </div>
  );
}
