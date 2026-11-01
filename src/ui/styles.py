"""All CSS for the Streamlit chat UI. Injected by app.py via st.markdown."""

from __future__ import annotations

CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg: #F6F8FA;
  --surface: #FFFFFF;
  --border: #E4E8EE;
  --text: #0B1B2B;
  --text-2: #5A6678;
  --brand: #00A67E;
  --user-bubble: #0B1B2B;
  --user-bubble-text: #FFFFFF;
  --ok: #00A67E;
  --ok-bg: #E6F6F0;
  --warn: #E8890C;
  --warn-bg: #FEF3E2;
  --neutral: #6B7A90;
  --neutral-bg: #EEF1F5;
  --err: #D92D20;
  --err-bg: #FDECEA;
  --radius-card: 12px;
  --radius-pill: 999px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0A1220;
    --surface: #121C2E;
    --border: #233048;
    --text: #E8EDF4;
    --text-2: #9AA7BB;
    --brand: #2DD4A4;
    --user-bubble: #1B2A44;
    --user-bubble-text: #E8EDF4;
    --ok: #2DD4A4;
    --ok-bg: #0F2E26;
    --warn: #F5A623;
    --warn-bg: #2E2410;
    --neutral: #9AA7BB;
    --neutral-bg: #1A2538;
    --err: #F06A5B;
    --err-bg: #2E1614;
  }
}

html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 15px;
  color: var(--text);
}

.stApp { background: var(--bg); }

header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"], [data-testid="stSidebar"], [data-testid="collapsedControl"] {
  display: none !important;
}

.block-container {
  max-width: 760px;
  margin: 0 auto;
  padding: 24px 20px 140px 20px;
}

/* Header bar */
.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0 16px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0; padding: 0; line-height: 1;
}
.logo-square {
  width: 32px; height: 32px; border-radius: 8px;
  background: var(--brand); color: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px; flex-shrink: 0;
  margin: 0; line-height: 1;
}
.header-title { font-size: 18px; font-weight: 600; color: var(--text); margin: 0; padding: 0; line-height: 1; }
.pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: var(--radius-pill);
  border: 1px solid var(--border); background: var(--surface);
  font-size: 12px; color: var(--text-2); white-space: nowrap;
  margin: 0; line-height: 1;
}
.pill .shield { color: var(--brand); }

/* Welcome */
.welcome { text-align: center; padding: 48px 0 24px 0; }
.welcome h2 { font-size: 22px; font-weight: 600; color: var(--text); margin: 0 0 8px 0; }
.welcome p { font-size: 15px; color: var(--text-2); margin: 0; line-height: 1.5; }
.starter-chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 24px; }
.starter-chips button {
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  border-radius: var(--radius-pill) !important;
  padding: 8px 14px !important;
  font-size: 13px !important;
  height: auto !important;
}
.starter-chips button:hover, .starter-chips button:focus-visible {
  border-color: var(--brand) !important;
  color: var(--brand) !important;
  outline: none !important;
  box-shadow: none !important;
}
.starter-chips button:focus { outline: none !important; box-shadow: none !important; }

/* Thread */
.thread { display: flex; flex-direction: column; gap: 20px; }
.turn { display: flex; flex-direction: column; gap: 8px; }
.turn.user { align-items: flex-end; }
.turn.assistant { align-items: flex-start; flex-direction: row; gap: 10px; }

/* User bubble */
.user-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 18px 18px 4px 18px;
  font-size: 15px;
  line-height: 1.5;
  background: var(--user-bubble);
  color: var(--user-bubble-text);
  word-wrap: break-word;
  overflow-wrap: break-word;
  white-space: pre-wrap;
}

/* Assistant avatar */
.avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--brand); color: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; flex-shrink: 0; margin-top: 2px;
}
.assistant-stack { max-width: 85%; display: flex; flex-direction: column; gap: 8px; }

/* Status chip */
.status-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: var(--radius-pill);
  font-size: 12px; font-weight: 500; border: 1px solid; margin-bottom: 4px;
}
.status-chip .dot { width: 6px; height: 6px; border-radius: 50%; }
.status-chip.ok { color: var(--ok); background: var(--ok-bg); border-color: var(--ok); }
.status-chip.ok .dot { background: var(--ok); }
.status-chip.warn { color: var(--warn); background: var(--warn-bg); border-color: var(--warn); }
.status-chip.warn .dot { background: var(--warn); }
.status-chip.neutral { color: var(--neutral); background: var(--neutral-bg); border-color: var(--neutral); }
.status-chip.neutral .dot { background: var(--neutral); }
.status-chip.err { color: var(--err); background: var(--err-bg); border-color: var(--err); }
.status-chip.err .dot { background: var(--err); }

/* Answer card */
.answer-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-card); padding: 16px; margin: 4px 0 8px 0;
  animation: fadeIn 200ms ease both;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
.hero-row { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
.hero-block { display: flex; flex-direction: column; }
.hero-label { font-size: 12px; color: var(--text-2); margin-bottom: 2px; }
.hero-number { font-size: 32px; font-weight: 600; line-height: 1; color: var(--text); }
.hero-secondary { font-size: 13px; color: var(--text-2); padding-bottom: 4px; }
.answer-text { font-size: 15px; line-height: 1.6; color: var(--text); }
.answer-text p { margin: 0; }

/* Source row */
.source-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 8px 0 4px 0; font-size: 12px; color: var(--text-2); }
.domain-chip { display: inline-flex; align-items: center; padding: 3px 8px; border-radius: var(--radius-pill); border: 1px solid var(--border); background: var(--surface); color: var(--brand); text-decoration: none; font-weight: 500; }
.domain-chip:hover { text-decoration: underline; }

/* Follow-up chips */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.chip-row button {
  border-radius: var(--radius-pill) !important;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  font-size: 13px !important;
  padding: 6px 12px !important;
  height: auto !important;
}
.chip-row button:hover, .chip-row button:focus-visible {
  border-color: var(--brand) !important;
  color: var(--brand) !important;
  outline: none !important;
  box-shadow: none !important;
}

/* Composer */
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"],
[data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea {
  background: transparent !important; box-shadow: none !important; background-image: none !important;
}
[data-testid="stBottom"] { padding: 0 !important; }
[data-testid="stBottomBlockContainer"] { max-width: 760px !important; margin: 0 auto !important; padding: 12px 20px 16px !important; }
[data-testid="stChatInput"] {
  border-radius: var(--radius-pill) !important;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  padding: 4px 8px !important;
  overflow: hidden !important;
}
[data-testid="stChatInput"] > div { border-radius: inherit !important; overflow: hidden !important; background: transparent !important; }
[data-testid="stChatInput"] textarea { font-size: 15px !important; color: var(--text) !important; background: transparent !important; }
[data-testid="stChatInput"] button { background: var(--brand) !important; color: #FFFFFF !important; border-radius: 50% !important; }
.composer-caption { text-align: center; font-size: 11px; color: var(--text-2); margin-top: 6px; }

/* Typing indicator */
.typing-indicator { display: inline-flex; align-items: center; gap: 4px; padding: 12px 16px; }
.typing-indicator span { width: 6px; height: 6px; border-radius: 50%; background: var(--text-2); animation: typing 1.2s infinite ease-in-out; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%,80%,100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }

.welcome { text-align: center; padding: 48px 0 24px 0; }
.welcome h2 { font-size: 22px; font-weight: 600; color: var(--text); margin: 0 0 8px 0; }
.welcome p { font-size: 15px; color: var(--text-2); margin: 0; line-height: 1.5; }

details { border: 1px solid var(--border); border-radius: 8px; padding: 4px 8px; background: var(--surface); margin: 4px 0; }
details summary { cursor: pointer; font-size: 12px; color: var(--text-2); font-weight: 500; }

@media (prefers-reduced-motion: reduce) {
  .answer-card { animation: none; }
  .typing-indicator span { animation: none; opacity: 0.7; }
}
</style>
"""


def inject() -> None:
    import streamlit as st

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>",
        unsafe_allow_html=True,
    )