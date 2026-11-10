"""All CSS for the Streamlit chat UI. Injected by app.py via st.markdown."""

from __future__ import annotations

CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@300;400;500;600&display=swap');

:root {
  --bg: #FFFFFF;
  --surface: #FFFFFF;
  --border: #E4E8EE;
  --glass-border: rgba(17,17,17,0.10);
  --text: #111111;
  --text-2: #6B665F;
  --brand: #E8500E;
  --user-bubble: #111111;
  --user-bubble-text: #FFFFFF;
  --ok: #E8500E;
  --ok-bg: #FDECEA;
  --warn: #E8890C;
  --warn-bg: #FEF3E2;
  --neutral: #6B665F;
  --neutral-bg: #EEF1F5;
  --err: #D92D20;
  --err-bg: #FDECEA;
  --radius-card: 12px;
  --radius-pill: 999px;
  --assistant-indent: 38px;
  --brand-tint: rgba(232,80,14,0.10);
  --on-brand: #FFFFFF;
  --s1: 4px;
  --s2: 8px;
  --s3: 12px;
  --s4: 16px;
  --s5: 24px;
  --s6: 32px;
  --s7: 48px;
}


html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 15px;
  font-weight: 400;
  line-height: 1.6;
  color: var(--text);
}

.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {
  background: #FFFFFF !important;
}

header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"],
[data-testid="stSidebar"], [data-testid="collapsedControl"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"],
.stAppDeployButton, [class*="viewerBadge"],
[data-testid="stHeaderActionElements"], .stMarkdown a.anchor-link,
[data-testid*="ScrollToBottom"] {
  display: none !important;
}

.block-container {
  max-width: 760px;
  margin: 0 auto;
  padding: 64px 20px 200px 20px;
  gap: 0 !important;
}
body.empty-state-active, body.empty-state-active .stApp, body.empty-state-active [data-testid="stAppViewContainer"], body.empty-state-active [data-testid="stMain"] {
  height: 100dvh; overflow: hidden;
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
  border-bottom: none;
  margin-bottom: var(--s5);
}
.header-left {
  display: flex; align-items: center; gap: var(--s3);
  margin: 0; padding: 0; line-height: 1;
}
.logo-square {
  width: 32px; height: 32px; border-radius: 8px;
  background: #111111; color: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 14px; flex-shrink: 0;
  margin: 0; line-height: 1;
}
.header-title { font-size: 18px; font-weight: 600; color: var(--text); margin: 0; padding: 0; line-height: 1; }
.pill {
  display: inline-flex; align-items: center; gap: var(--s2);
  padding: var(--s2) var(--s3); border-radius: var(--radius-pill);
  border: 1px solid rgba(17,17,17,0.10); background: rgba(255,255,255,0.55);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  font-size: 12px; color: #111111; white-space: nowrap;
  margin: 0; line-height: 1;
}
.pill .shield { color: #111111; }

/* Empty state */
.empty-state {
  display: grid;
  grid-template-rows: 1fr auto 112px;
  height: 100dvh;
  overflow: hidden;
  padding-top: 64px;
}
@media (max-width: 600px) { .empty-state { padding-top: 32px; } }
.empty-middle { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }
.empty-state .sphere {
  width: 190px; height: 190px; border-radius: 50%;
  margin: 0 auto 16px;
  background: radial-gradient(circle at 34% 28%, #FFB886 0%, #FF7A1A 34%, #E8500E 68%, #B93A06 100%);
  box-shadow: 0 26px 64px rgba(232,80,14,0.40);
  border: none;
  transition: opacity 500ms ease;
}
@media (max-width: 600px) { .empty-state .sphere { width: 150px; height: 150px; } }
.sphere.fading { opacity: 0; }
  background: radial-gradient(circle at 34% 28%, #FFB886 0%, #FF7A1A 34%, #E8500E 68%, #B93A06 100%);
  box-shadow: 0 26px 64px rgba(232,80,14,0.40);
  border: none;
  transition: opacity 500ms ease;
}
.sphere.fading { opacity: 0; }
@media (max-width: 600px) { .sphere { width: 150px; height: 150px; } }
@media (prefers-reduced-motion: reduce) { .sphere { transition: none; } }

.welcome { text-align: center; }
.welcome h2 {
  font-family: 'Outfit', 'Inter', sans-serif;
  font-weight: 300; font-size: 28px; color: var(--text);
  margin: 0 0 8px 0; line-height: 1.2;
}
@media (max-width: 600px) { .welcome h2 { font-size: 22px; } }
.welcome p { font-size: 13px; color: var(--text-2); margin: 0; line-height: 1.5; }

.empty-composer { max-width: 640px; margin: 24px auto 16px; }
.empty-composer [data-testid="stChatInput"] { max-width: 640px !important; margin: 0 auto !important; min-height: 56px !important; }

.starter-chips {
  display: flex; flex-wrap: wrap; justify-content: center; gap: 8px;
  margin: 16px 0 0 0;
  padding: 0;
  position: static; transform: none;
}
.starter-chips .chip { display: inline-block; padding: 8px 16px; border: 1px solid rgba(17,17,17,0.14); border-radius: 999px; background: #FFFFFF; color: #111111; font-size: 13px; text-decoration: none; white-space: nowrap; opacity: 1 !important; }
.starter-chips .chip:hover, .starter-chips .chip:focus-visible { border-color: #C23E08; color: #C23E08; outline: none; }

.composer-caption { position: fixed; bottom: 4px; left: 50%; transform: translateX(-50%); max-width: 760px; width: 100%; text-align: center; font-size: 11px; color: var(--text-2); padding: 0 16px; z-index: 101; margin: 0; }

/* Thread */
.thread { display: flex; flex-direction: column; gap: var(--s6); }
.turn { display: flex; flex-direction: column; gap: var(--s4); }
.turn.user { align-items: flex-end; }
.turn.assistant { align-items: flex-start; flex-direction: row; gap: 10px; }

/* User bubble */
.user-bubble {
  max-width: 75%; padding: 10px 14px;
  border-radius: 18px 18px 4px 18px;
  font-size: 15px; line-height: 1.6;
  background: var(--user-bubble); color: var(--user-bubble-text);
  word-wrap: break-word; overflow-wrap: break-word; white-space: pre-wrap;
}

/* Assistant avatar */
.avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: #111111; color: #FFFFFF;
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
  background: var(--surface); border: 1px solid var(--glass-border);
  border-radius: var(--radius-card); padding: var(--s4) var(--s5);
  margin: 0; animation: fadeIn 200ms ease both;
  box-shadow: none;
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
  border: 1px solid var(--glass-border); background: var(--surface);
  color: var(--brand); text-decoration: none; font-weight: 500;
}
.domain-chip:hover { text-decoration: underline; }

/* Follow-up pills */
[data-testid="stPills"] {
  margin-top: var(--s3);
  margin-left: var(--assistant-indent);
  padding-left: 0 !important;
  display: flex; flex-wrap: wrap; gap: 8px;
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

/* Composer */
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"],
[data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] div[data-baseweb="textarea"],
[data-testid="stChatInput"] div[data-baseweb="base-input"] {
  background: transparent !important; box-shadow: none !important; background-image: none !important;
  outline: none !important; border-color: transparent !important;
}
[data-testid="stBottom"] {
  position: fixed !important;
  left: 0 !important; right: 0 !important; bottom: 0 !important;
  z-index: 100 !important;
  background: transparent !important;
  padding: 0 !important;
}
[data-testid="stBottomBlockContainer"] {
  max-width: 760px !important;
  margin: 0 auto !important;
  padding: 0 16px 20px !important;
  background: transparent !important;
}
[data-testid="stChatInput"] {
  border-radius: var(--radius-pill) !important;
  border: 1px solid var(--glass-border) !important;
  background: rgba(255,255,255,0.55) !important;
  backdrop-filter: blur(16px) saturate(1.4) !important;
  -webkit-backdrop-filter: blur(16px) saturate(1.4) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9) !important;
  padding: 4px 8px !important;
  overflow: hidden !important;
  transition: border-color 150ms ease;
}

[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] div[data-baseweb="textarea"],
[data-testid="stChatInput"] div[data-baseweb="base-input"] {
  border-radius: inherit !important; overflow: hidden !important; background: transparent !important; border: none !important;
}
[data-testid="stChatInput"] textarea { font-size: 15px !important; color: var(--text) !important; background: transparent !important; }
[data-testid="stChatInput"] button { background: #111111 !important; color: #FFFFFF !important; border-radius: 50% !important; border: none !important; outline: none !important; box-shadow: none !important; }
[data-testid="stChatInput"]:focus-within { border-color: #C23E08 !important; }
@media (prefers-reduced-motion: reduce) {
  [data-testid="stChatInput"] { transition: none !important; }
}

/* Typing indicator */
.typing-indicator { display: inline-flex; align-items: center; gap: var(--s2); padding: var(--s4) var(--s5); }
.typing-indicator span { width: 6px; height: 6px; border-radius: 50%; background: var(--text-2); animation: typing 1.2s infinite ease-in-out; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%,80%,100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }

.welcome { text-align: center; padding: 0 0 var(--s5) 0; }
.welcome h2 { font-family: 'Outfit', 'Inter', sans-serif; font-weight: 300; font-size: 28px; color: var(--text); margin: 0 0 8px 0; line-height: 1.2; }
@media (max-width: 600px) { .welcome h2 { font-size: 22px; } }
.welcome p { font-size: 13px; color: var(--text-2); margin: 0; line-height: 1.5; }

details { border: 1px solid var(--border); border-radius: 8px; padding: var(--s1) var(--s2); background: var(--surface); margin: var(--s1) 0; }
details summary { cursor: pointer; font-size: 12px; color: var(--text-2); font-weight: 500; }

/* Orange glow */
.glow {
  position: fixed;
  bottom: 0; left: 50%;
  transform: translateX(-50%);
  width: 520px; height: 160px;
  background: radial-gradient(ellipse at center, rgba(255,122,26,0.18), transparent 70%);
  pointer-events: none;
  z-index: 0;
  opacity: 0.18;
  transition: opacity 500ms ease;
}
.glow.fading { opacity: 0 !important; }
@media (prefers-reduced-motion: reduce) { .glow { transition: none; } }

@media (prefers-reduced-motion: reduce) {
  .answer-card { animation: none; }
  .typing-indicator span { animation: none; opacity: 0.7; }
  .sphere { transition: none; }
}
</style>
"""


def inject() -> None:
    import streamlit as st

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@300;400;500;600&display=swap' rel='stylesheet'>",
        unsafe_allow_html=True,
    )