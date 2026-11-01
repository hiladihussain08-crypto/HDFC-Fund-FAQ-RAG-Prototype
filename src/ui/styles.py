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
  --assistant-indent: 38px;
  --brand-tint: rgba(0,166,126,0.10);
  --on-brand: #FFFFFF;
  --s1: 4px;
  --s2: 8px;
  --s3: 12px;
  --s4: 16px;
  --s5: 24px;
  --s6: 32px;
  --s7: 48px;
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
    --brand-tint: rgba(45,212,164,0.12);
    --on-brand: #04261C;
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
  font-weight: 400;
  line-height: 1.6;
  color: var(--text);
}

.stApp { background: var(--bg); }

button, a { outline: none !important; }
button:focus, button:focus-visible, a:focus, a:focus-visible {
  outline: none !important;
  box-shadow: none !important;
}

header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"],
[data-testid="stSidebar"], [data-testid="collapsedControl"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"],
.stAppDeployButton, [class*="viewerBadge"],
[data-testid="stHeaderActionElements"], .stMarkdown a.anchor-link {
  display: none !important;
}

.block-container {
  max-width: 760px;
  margin: 0 auto;
  padding: 64px 20px 180px 20px;
  gap: 0 !important;
}
@media (max-width: 600px) {
  .block-container { padding-top: 32px; }
}

/* Header bar */
.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
  padding: var(--s2) 0 var(--s4) 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--s5);
}
.header-left {
  display: flex;
  align-items: center;
  gap: var(--s3);
  margin: 0; padding: 0; line-height: 1;
}
.logo-square {
  width: 32px; height: 32px; border-radius: 8px;
  background: var(--brand); color: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 14px; flex-shrink: 0;
  margin: 0; line-height: 1;
}
.header-title { font-size: 18px; font-weight: 600; color: var(--text); margin: 0; padding: 0; line-height: 1; }
.pill {
  display: inline-flex; align-items: center; gap: var(--s2);
  padding: var(--s2) var(--s3); border-radius: var(--radius-pill);
  border: 1px solid var(--border); background: var(--surface);
  font-size: 12px; color: var(--text-2); white-space: nowrap;
  margin: 0; line-height: 1;
}
.pill .shield { color: var(--brand); }

/* Welcome */
.welcome { text-align: center; padding: var(--s7) 0 var(--s5) 0; }
.welcome h2 { font-size: 22px; font-weight: 600; color: var(--text); margin: 0 0 var(--s2) 0; }
.welcome p { font-size: 15px; color: var(--text-2); margin: 0; line-height: 1.6; }
.starter-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 16px; }
.starter-chips .chip { display: inline-block; padding: 8px 16px; border: 1px solid var(--border); border-radius: 999px; background: var(--surface); color: var(--text); font-size: 14px; text-decoration: none; white-space: nowrap; }
.starter-chips .chip:hover, .starter-chips .chip:focus-visible { border-color: var(--brand); outline: none; }

/* Thread */
.thread { display: flex; flex-direction: column; gap: var(--s6); }
.turn { display: flex; flex-direction: column; gap: var(--s4); }
.turn.user { align-items: flex-end; }
.turn.assistant { align-items: flex-start; flex-direction: row; gap: 10px; }

/* User bubble */
.user-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 18px 18px 4px 18px;
  font-size: 15px;
  line-height: 1.6;
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
  font-size: 13px; font-weight: 600; flex-shrink: 0; margin-top: var(--s1);
}
.assistant-stack { max-width: 85%; display: flex; flex-direction: column; gap: var(--s3); }

/* Status chip */
.status-chip {
  display: inline-flex; align-items: center; gap: var(--s2);
  width: fit-content; align-self: flex-start;
  padding: 4px 10px; border-radius: var(--radius-pill);
  font-size: 12px; font-weight: 500; border: 1px solid; margin-bottom: var(--s2);
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
  border-radius: var(--radius-card);
  padding: var(--s4) var(--s5);
  margin: 0;
  animation: fadeIn 200ms ease both;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
.hero-row { display: flex; flex-direction: column; gap: var(--s2); margin-bottom: var(--s2); }
.hero-block { display: flex; flex-direction: column; }
.hero-label { font-size: 12px; color: var(--text-2); margin-bottom: var(--s1); }
.hero-number { font-size: 32px; font-weight: 600; line-height: 1; color: var(--text); }
.hero-secondary { font-size: 13px; color: var(--text-2); }
.answer-text { font-size: 15px; line-height: 1.6; color: var(--text); }
.answer-text p { margin: 0; }

/* Source row */
.source-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--s3); flex-wrap: wrap;
  margin: var(--s3) 0 var(--s2) 0;
  font-size: 12px; color: var(--text-2);
  border: none;
}
.source-row-left { display: flex; align-items: center; gap: var(--s2); flex-wrap: wrap; }
.domain-chip {
  display: inline-flex; align-items: center;
  padding: 3px 8px; border-radius: var(--radius-pill);
  border: 1px solid var(--border); background: var(--surface);
  color: var(--brand); text-decoration: none; font-weight: 500;
}
.domain-chip:hover { text-decoration: underline; }
.how-link { font-size: 12px; color: var(--text-2); cursor: pointer; text-decoration: underline; }

/* Follow-up chips */
.chip-row { display: flex; flex-wrap: wrap; gap: var(--s2); margin-top: var(--s3); border: none; }
.chip-row button, .chip {
  border-radius: var(--radius-pill) !important;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  color: var(--text) !important;
  font-size: 13px !important;
  padding: var(--s2) var(--s3) !important;
  height: auto !important;
  font-weight: 400 !important;
  cursor: pointer;
}
.chip-row button:hover, .chip-row button:focus-visible,
.chip:hover, .chip:focus-visible {
  border-color: var(--brand) !important;
  color: var(--brand) !important;
  outline: none !important;
  box-shadow: none !important;
}

/* Composer */
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"],
[data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] div[data-baseweb="textarea"],
[data-testid="stChatInput"] div[data-baseweb="base-input"] {
  background: transparent !important;
  box-shadow: none !important;
  background-image: none !important;
  outline: none !important;
  border-color: transparent !important;
}
[data-testid="stBottom"] { padding: 0 !important; }
[data-testid="stBottomBlockContainer"] { max-width: 760px !important; margin: 0 auto !important; padding: var(--s3) 20px var(--s4) !important; }

[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] div[data-baseweb="textarea"],
[data-testid="stChatInput"] div[data-baseweb="base-input"],
[data-testid="stChatInput"] textarea {
  outline: none !important;
  box-shadow: none !important;
  border: none !important;
}

[data-testid="stChatInput"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-pill) !important;
  background: var(--surface) !important;
  padding: 4px 8px !important;
  overflow: hidden !important;
  transition: border-color 150ms ease;
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--brand) !important;
}
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] div[data-baseweb="textarea"],
[data-testid="stChatInput"] div[data-baseweb="base-input"] {
  border-radius: inherit !important;
  background: transparent !important;
}
[data-testid="stChatInput"] textarea { font-size: 15px !important; color: var(--text) !important; background: transparent !important; }
[data-testid="stChatInput"] button { background: var(--brand) !important; color: #FFFFFF !important; border-radius: 50% !important; border: none !important; outline: none !important; box-shadow: none !important; }

@media (prefers-reduced-motion: reduce) {
  [data-testid="stChatInput"] { transition: none !important; }
}
.composer-caption { text-align: center; font-size: 11px; color: var(--text-2); margin-top: var(--s2); }

/* Follow-up pills */
[data-testid="stPills"] {
  margin-top: var(--s3);
  margin-left: var(--assistant-indent);
  padding-left: 0 !important;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
[data-testid="stPills"] button,
[data-testid="stButtonGroup"] button,
[data-testid="stPills"] [data-baseweb="button-group"] button {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  font-size: 14px !important;
  padding: 8px 16px !important;
  border-radius: var(--radius-pill) !important;
  outline: none !important;
  box-shadow: none !important;
  transition: border-color 150ms ease, color 150ms ease, background 150ms ease;
}
[data-testid="stPills"] button:hover,
[data-testid="stPills"] button:focus-visible,
[data-testid="stPills"] [data-baseweb="button-group"] button:hover,
[data-testid="stPills"] [data-baseweb="button-group"] button:focus-visible,
[data-testid="stButtonGroup"] button:hover,
[data-testid="stButtonGroup"] button:focus-visible {
  background: var(--brand-tint) !important;
  border-color: var(--brand) !important;
  color: var(--brand) !important;
  outline: none !important;
  box-shadow: none !important;
}
[data-testid="stPills"] button:active,
[data-testid="stPills"] button[aria-pressed="true"],
[data-testid="stPills"] button[aria-checked="true"],
[data-testid="stPills"] button[data-selected],
[data-testid="stPills"] [data-baseweb="button-group"] button:active,
[data-testid="stPills"] [data-baseweb="button-group"] button[aria-pressed="true"],
[data-testid="stPills"] [data-baseweb="button-group"] button[aria-checked="true"],
[data-testid="stPills"] [data-baseweb="button-group"] button[data-selected],
[data-testid="stButtonGroup"] button:active,
[data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[data-selected] {
  background: var(--brand) !important;
  border-color: var(--brand) !important;
  color: var(--on-brand) !important;
  outline: none !important;
  box-shadow: none !important;
}
[data-testid="stPills"] button p,
[data-testid="stPills"] button span,
[data-testid="stPills"] button div,
[data-testid="stPills"] [data-baseweb="button-group"] button p,
[data-testid="stPills"] [data-baseweb="button-group"] button span,
[data-testid="stPills"] [data-baseweb="button-group"] button div,
[data-testid="stButtonGroup"] button p,
[data-testid="stButtonGroup"] button span,
[data-testid="stButtonGroup"] button div {
  color: inherit !important;
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stPills"] button,
  [data-testid="stPills"] [data-baseweb="button-group"] button,
  [data-testid="stButtonGroup"] button {
    transition: none !important;
  }
}

/* Typing indicator */
.typing-indicator { display: inline-flex; align-items: center; gap: var(--s2); padding: var(--s4) var(--s5); }
.typing-indicator span { width: 6px; height: 6px; border-radius: 50%; background: var(--text-2); animation: typing 1.2s infinite ease-in-out; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%,80%,100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }

.welcome { text-align: center; padding: var(--s7) 0 var(--s5) 0; }
.welcome h2 { font-size: 22px; font-weight: 600; color: var(--text); margin: 0 0 var(--s2) 0; }
.welcome p { font-size: 15px; color: var(--text-2); margin: 0; line-height: 1.6; }

details { border: 1px solid var(--border); border-radius: 8px; padding: var(--s1) var(--s2); background: var(--surface); margin: var(--s1) 0; }
details summary { cursor: pointer; font-size: 12px; color: var(--text-2); font-weight: 500; }

.empty-state { padding-top: 0; }
.empty-composer [data-testid="stChatInput"] { max-width: 640px !important; margin: 0 auto !important; min-height: 56px !important; }
.empty-state .welcome { margin-bottom: var(--s2); }
.empty-state .welcome p { margin-bottom: var(--s5); }
.empty-composer { margin-bottom: var(--s3); }
.starter-chips { margin-bottom: var(--s5); }
.thread.fade-in { animation: fadeIn 200ms ease both; }

@media (prefers-reduced-motion: reduce) {
  .answer-card { animation: none; }
  .typing-indicator span { animation: none; opacity: 0.7; }
  .thread.fade-in { animation: none; }
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