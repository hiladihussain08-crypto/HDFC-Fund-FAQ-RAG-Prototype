"""Streamlit chatbot UI for the Groww MF FAQ Assistant (redesign)."""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402
import streamlit.components.v1 as components  # noqa: E402

from src.config import load_config  # noqa: E402
from src.query.pipeline import answer_question  # noqa: E402
from src.schemes import SCHEME_BY_ID  # noqa: E402
from src.ui.styles import inject as inject_styles  # noqa: E402
from src.utils import read_json  # noqa: E402

st.set_page_config(page_title="Fund FAQ assistant", page_icon="💬", layout="wide", initial_sidebar_state="collapsed")

config = load_config()
inject_styles()

FOLLOWUPS: dict[str, list[str]] = {
    "expense_ratio": ["Exit load", "Minimum SIP", "Fund manager"],
    "exit_load": ["Expense ratio", "Minimum SIP", "Fund manager"],
    "min_sip": ["Expense ratio", "Exit load", "Fund manager"],
    "min_investment": ["Expense ratio", "Exit load", "Minimum SIP"],
    "fund_manager": ["Expense ratio", "Exit load", "Minimum SIP"],
    "fund_house": ["Expense ratio", "Exit load", "Minimum SIP"],
    "aum": ["Expense ratio", "Exit load", "Minimum SIP"],
    "category": ["Expense ratio", "Exit load", "Minimum SIP"],
    "lock_in": ["Expense ratio", "Exit load", "Minimum SIP"],
    "riskometer": ["Expense ratio", "Exit load", "Minimum SIP"],
    "benchmark": ["Expense ratio", "Exit load", "Minimum SIP"],
    "launch_date": ["Expense ratio", "Exit load", "Minimum SIP"],
    "stamp_duty": ["Expense ratio", "Exit load", "Minimum SIP"],
}

CHIP_TOPIC = {
    "Expense ratio": "expense ratio",
    "Exit load": "exit load",
    "Minimum SIP": "minimum SIP",
    "Fund manager": "fund manager",
}

INTENT_LABEL = {
    "expense_ratio": "Expense ratio",
    "exit_load": "Exit load",
    "min_sip": "Minimum SIP",
    "min_investment": "Minimum investment",
    "fund_manager": "Fund manager",
    "fund_house": "Fund house",
    "aum": "AUM",
    "category": "Category",
    "lock_in": "Lock-in",
    "riskometer": "Riskometer",
    "benchmark": "Benchmark",
    "launch_date": "Launch date",
    "stamp_duty": "Stamp duty",
}

_HERO_RE = re.compile(r"(₹\s?[\d,]+(?:\.\d+)?|\d[\d,]*\.?\d*\s*%)")
_STARTERS = ["Expense ratio", "Exit load", "Minimum SIP", "Fund manager"]

st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending_prompt", "")
st.session_state.setdefault("pending_question", "")
st.session_state.setdefault("started", False)


def handle_followup(turn_index: int) -> None:
    key = f"followup_{turn_index}"
    selected = st.session_state.get(key)
    if not selected:
        return
    msg = st.session_state.messages[turn_index] if turn_index < len(st.session_state.messages) else None
    fund = "HDFC Large Cap Fund Direct Growth"
    if msg and msg.get("fund"):
        fund = msg["fund"]
    topic = CHIP_TOPIC.get(selected, selected.lower())
    st.session_state.pending_question = f"What is the {topic} of {fund}?"
    st.session_state[key] = None


def status_for(route: str) -> tuple[str, str]:
    if route == "answer":
        return "ok", "Factual answer"
    if route and route.startswith("refuse"):
        return "warn", "I can't advise on that"
    if route == "miss":
        return "neutral", "Not in my data"
    return "err", "Something went wrong"


def extract_hero(answer: str):
    m = _HERO_RE.search(answer)
    if not m:
        return None, None
    hero = m.group(0).strip()
    pm = re.search(r"\(([^)]+)\)", answer)
    secondary = pm.group(1).strip() if pm else None
    return hero, secondary


def format_updated(last_updated: str) -> str:
    stamp = last_updated.replace("Last updated from sources:", "").strip()
    try:
        dt = datetime.strptime(stamp, "%Y-%m-%d")
        return f"Updated {dt.day} {dt.strftime('%b %Y')}"
    except ValueError:
        return last_updated


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:  # noqa: BLE001
        return url


def esc(s) -> str:
    return html.escape(str(s) if s is not None else "")


def render_user(content: str) -> str:
    return f'<div class="turn user"><div class="user-bubble">{esc(content)}</div></div>'


def render_assistant(response: dict) -> str:
    status_class, status_label = status_for(response["route"])
    route = response["route"]
    intent = response.get("intent", "other")
    answer = response["answer"]

    hero, secondary = (extract_hero(answer) if route == "answer" else (None, None))

    if route == "answer" and hero:
        label = INTENT_LABEL.get(intent, intent.replace("_", " ").title())
        secondary_html = f'<span class="hero-secondary">{esc(secondary)}</span>' if secondary else ""
        card_html = (
            f'<div class="answer-card">'
            f'  <div class="hero-row">'
            f'    <div class="hero-block">'
            f'      <div class="hero-label">{esc(label)}</div>'
            f'      <div class="hero-number">{esc(hero)}</div>'
            f'    </div>'
            f'    {secondary_html}'
            f'  </div>'
            f'</div>'
        )
    else:
        card_html = (
            f'<div class="answer-card">'
            f'  <div class="answer-text"><p>{esc(answer)}</p></div>'
            f'</div>'
        )

    source_html = ""
    citation_url = response.get("citation_url", "")
    if citation_url:
        domain = domain_of(citation_url)
        source_html = (
            f'<div class="source-row">'
            f'  <span class="source-row-left">'
            f'    <a class="domain-chip" href="{esc(citation_url)}" target="_blank" rel="noopener noreferrer">{esc(domain)}</a>'
            f'    <span style="display:inline-flex;align-items:center;gap:4px;">'
            f'      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
            f'      {esc(format_updated(response.get("last_updated", "")))}'
            f'    </span>'
            f'  </span>'
            f'  <details style="margin:0;"><summary style="cursor:pointer;font-size:12px;color:var(--text-2);font-weight:500;list-style:none;">How this was answered</summary>'
            f'    <div style="margin-top:8px;">'
            f'      <div>Mode: {esc(response["generation"].get("mode", "policy"))}</div>'
            f'      <div>Intent: {esc(intent)}</div>'
            f'      <div>Latency: {response["latency_ms"]} ms</div>'
            f'      <div>Query ID: {esc(response["query_id"])}</div>'
        )
        if response.get("hits"):
            source_html += '      <div style="margin-top:8px;font-weight:600;">Retrieved chunks</div>'
            for hit in response["hits"]:
                source_html += (
                    f'      <div style="margin:4px 0;"><strong>{hit["score"]:.3f}</strong> · {esc(hit.get("heading", ""))} · {esc(hit.get("source_title", ""))}</div>'
                    f'      <div style="font-size:12px;color:var(--text-2);">{esc(hit.get("text", "")[:400])}</div>'
                    f'      <div style="font-size:12px;color:var(--text-2);">Citation: {esc(hit.get("source_url", ""))}</div>'
                )
        source_html += '      <div style="margin-top:8px;font-weight:600;">Stage artifacts</div>'
        for label, path in response["artifacts"].items():
            try:
                content = json.dumps(read_json(Path(path)), indent=2, ensure_ascii=False)
            except Exception:  # noqa: BLE001
                content = f"Could not read {path}"
            source_html += (
                f'      <div style="font-weight:500;margin-top:4px;">{esc(label)} — {esc(path)}</div>'
                f'      <pre style="font-size:11px;max-height:200px;overflow:auto;background:var(--bg);padding:8px;border-radius:6px;">{esc(content)}</pre>'
            )
        source_html += '    </div></details></div>'

    status_class, status_label = status_for(route)
    avatar_html = '<div class="avatar">F</div>'
    stack_html = (
        f'<span class="status-chip {status_class}"><span class="dot"></span>{esc(status_label)}</span>'
        + card_html
        + source_html
    )

    return f'<div class="turn assistant">{avatar_html}<div class="assistant-stack">{stack_html}</div></div>'


def render_followups(turn_index: int) -> None:
    if turn_index >= len(st.session_state.messages):
        return
    msg = st.session_state.messages[turn_index]
    if msg.get("role") != "assistant":
        return
    last_assistant = None
    for i in range(len(st.session_state.messages) - 1, -1, -1):
        if st.session_state.messages[i].get("role") == "assistant":
            last_assistant = i
            break
    if turn_index != last_assistant:
        return
    response = msg["response"]
    route = response.get("route", "")
    if route != "answer":
        return
    intent = response.get("intent", "other")
    chips = FOLLOWUPS.get(intent, [])[:3]
    if not chips:
        return
    key = f"followup_{turn_index}"
    st.pills(
        "Follow-up",
        options=chips,
        selection_mode="single",
        label_visibility="collapsed",
        key=key,
        on_change=handle_followup,
        args=(turn_index,),
    )


# ---------- header ----------
st.markdown(
    '<div class="header-bar">'
    '  <div class="header-left">'
    '    <div class="logo-square">F</div>'
    '    <div class="header-title">Fund FAQ assistant</div>'
    '  </div>'
    '  <span class="pill"><span class="shield">🛡</span> Facts only, no advice</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ---------- handle chip query param (starter chips) ----------
qp = st.query_params
if "q" in qp:
    qval = qp["q"]
    if isinstance(qval, list):
        qval = qval[0] if qval else ""
    if qval:
        st.session_state.pending_prompt = qval
        st.session_state.started = True
    st.query_params.clear()

# ---------- handle pending questions (starter or follow-up) ----------
if st.session_state.pending_prompt:
    st.session_state.pending_question = st.session_state.pending_prompt
    st.session_state.pending_prompt = ""

if st.session_state.pending_question:
    pq = st.session_state.pending_question
    st.session_state.pending_question = ""
    st.session_state.started = True
    st.session_state.has_started = True
    st.session_state.messages.append({"role": "user", "content": pq})
    with st.spinner("Retrieving official pages and checking the facts…"):
        try:
            response = answer_question(pq, config, persist=True)
        except Exception:  # noqa: BLE001
            st.error("The pipeline is not ready. Run the ingest steps first, then try again.")
            st.stop()
    scheme = SCHEME_BY_ID.get(response.get("scheme", ""))
    st.session_state.messages.append({
        "role": "assistant",
        "response": response,
        "fund": scheme.name if scheme else None,
        "intent": response.get("intent"),
    })
    for k in list(st.session_state.keys()):
        if k.startswith("followup_"):
            st.session_state[k] = None
    st.rerun()

# ---------- empty state ----------
if not st.session_state.started and not st.session_state.messages:
    st.markdown('<div class="empty-state">', unsafe_allow_html=True)
    st.markdown('<div class="empty-middle">', unsafe_allow_html=True)
    st.markdown('<div class="sphere" id="sphere"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="welcome"><h2>Ask about any mutual fund</h2>'
        '<p>Factual answers from official fund pages, with one citation per answer.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
    chip_qs = {
        "Expense ratio": "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
        "Exit load": "What is the exit load of HDFC Large Cap Fund Direct Growth?",
        "Minimum SIP": "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
        "Fund manager": "Who is the fund manager of HDFC Large Cap Fund Direct Growth?",
    }
    chips_html = '<div class="starter-chips">'
    for label in _STARTERS:
        q = quote_plus(chip_qs[label])
        chips_html += f'<a class="chip" href="?q={q}" target="_self">{esc(label)}</a>'
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)
    st.markdown('<div style="height:112px;"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        """<script>
(function(){
  function attach(){
    const inp = document.querySelector('[data-testid="stChatInput"] textarea');
    const sphere = document.getElementById('sphere');
    const glow = document.getElementById('glow');
    if(!inp) return;
    inp.addEventListener('input', function(){
      if(inp.value.trim().length>0){
        if(sphere) sphere.classList.add('fading');
        if(glow) glow.classList.add('fading');
      } else {
        if(sphere) sphere.classList.remove('fading');
        if(glow) glow.classList.remove('fading');
      }
    });
  }
  setTimeout(attach, 500);
})();
</script>""",
        unsafe_allow_html=True,
    )

# ---------- transcript ----------
if st.session_state.started or st.session_state.messages:
    st.markdown('<div class="thread fade-in" id="thread">', unsafe_allow_html=True)
    for idx, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            st.markdown(render_user(message["content"]), unsafe_allow_html=True)
        else:
            st.markdown(render_assistant(message["response"]), unsafe_allow_html=True)
            render_followups(idx)
    st.markdown('<div id="thread-bottom" style="height:1px;"></div></div>', unsafe_allow_html=True)

# ---------- input (single, top level) ----------
prompt = st.chat_input("Ask about expense ratio, exit load, SIP…")

if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = ""

if prompt and not st.session_state.pending_question:
    st.session_state.started = True
    st.session_state.has_started = True
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(render_user(prompt), unsafe_allow_html=True)

    placeholder = st.empty()
    placeholder.markdown(
        '<div class="turn assistant"><div class="avatar">F</div>'
        '<div class="assistant-stack"><div class="typing-indicator"><span></span><span></span><span></span></div></div></div>',
        unsafe_allow_html=True,
    )
    try:
        response = answer_question(prompt, config, persist=True)
    except Exception:  # noqa: BLE001
        placeholder.empty()
        st.error("The pipeline is not ready. Run the ingest steps first, then try again.")
        st.stop()
    placeholder.empty()
    st.markdown(render_assistant(response), unsafe_allow_html=True)
    scheme = SCHEME_BY_ID.get(response.get("scheme", ""))
    st.session_state.messages.append({
        "role": "assistant",
        "response": response,
        "fund": scheme.name if scheme else None,
        "intent": response.get("intent"),
    })
    render_followups(len(st.session_state.messages) - 1)

# glow
glow_opacity = "0.10" if st.session_state.started else "0.18"
st.markdown(f'<div class="glow" id="glow" style="opacity:{glow_opacity};"></div>', unsafe_allow_html=True)

# body class toggle for scroll lock
st.markdown(
    f"<script>document.body.classList.toggle('empty-state-active', {'true' if not st.session_state.started else 'false'});</script>",
    unsafe_allow_html=True,
)

components.html(
    "<script>var el=window.parent.document.getElementById('thread-bottom'); if(el) el.scrollIntoView({behavior:'smooth',block:'end'});</script>",
    height=0,
)

st.markdown('<div class="composer-caption">Facts from public fund pages. Not investment advice.</div>',
            unsafe_allow_html=True)