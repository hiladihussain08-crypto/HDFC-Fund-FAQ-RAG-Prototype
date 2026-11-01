"""Streamlit chatbot UI for the Groww MF FAQ Assistant (redesign)."""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

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


def hero_remainder(answer: str, hero: str, secondary: str | None) -> str:
    text = answer
    text = text.replace(hero, "", 1)
    if secondary:
        text = text.replace(f"({secondary})", "", 1)
    text = " ".join(text.split())
    return text


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


def render_user(content: str) -> None:
    st.markdown(
        f'<div class="turn user"><div class="user-bubble">{html.escape(content)}</div></div>',
        unsafe_allow_html=True,
    )


def render_assistant(response: dict) -> None:
    status_class, status_label = status_for(response["route"])
    route = response["route"]
    intent = response.get("intent", "other")
    answer = response["answer"]

    hero, secondary = (extract_hero(answer) if route == "answer" else (None, None))

    # Answer card
    if route == "answer" and hero:
        label = INTENT_LABEL.get(intent, intent.replace("_", " ").title())
        secondary_html = f'<span class="hero-secondary">{html.escape(secondary)}</span>' if secondary else ""
        remainder = hero_remainder(answer, hero, secondary)
        extra_html = f'<div class="answer-text"><p>{html.escape(remainder)}</p></div>' if len(remainder) > 25 else ""
        card_html = (
            f'<div class="answer-card">'
            f'  <div class="hero-row">'
            f'    <div class="hero-block">'
            f'      <div class="hero-label">{html.escape(label)}</div>'
            f'      <div class="hero-number">{html.escape(hero)}</div>'
            f'    </div>'
            f'    {secondary_html}'
            f'  </div>'
            f'  {extra_html}'
            f'</div>'
        )
    else:
        card_html = (
            f'<div class="answer-card">'
            f'  <div class="answer-text"><p>{html.escape(answer)}</p></div>'
            f'</div>'
        )

    source_html = ""
    citation_url = response.get("citation_url", "")
    if citation_url:
        domain = domain_of(citation_url)
        source_html = (
            f'<div class="source-row">'
            f'  <a class="domain-chip" href="{html.escape(citation_url)}" target="_blank" rel="noopener noreferrer">{html.escape(domain)}</a>'
            f'  <span style="display:inline-flex;align-items:center;gap:4px;">'
            f'    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
            f'    {html.escape(format_updated(response.get("last_updated", "")))}'
            f'  </span>'
            f'</div>'
        )

    chips_html = ""
    if route == "answer":
        scheme = SCHEME_BY_ID.get(response.get("scheme", ""))
        chips = FOLLOWUPS.get(intent, [])
        if scheme and chips:
            chips_html = '<div class="chip-row">' + "".join(
                f'<button class="chip" data-chip="{html.escape(chip)}">{html.escape(chip)}</button>'
                for chip in chips
            ) + "</div>"

    avatar_html = '<div class="avatar">F</div>'
    stack_html = (
        f'<span class="status-chip {status_class}"><span class="dot"></span>{status_label}</span>'
        + card_html
        + source_html
        + f'<div class="meta">mode={html.escape(str(response["generation"].get("mode", "policy")))} · intent={html.escape(intent)} · {response["latency_ms"]} ms · query_id={html.escape(response["query_id"])}</div>'
        + chips_html
    )

    st.markdown(
        f'<div class="turn assistant">{avatar_html}<div class="assistant-stack">{stack_html}</div></div>',
        unsafe_allow_html=True,
    )

    # How this was answered expander
    with st.expander("How this was answered", expanded=False):
        st.markdown(
            f"**Mode:** {response['generation'].get('mode', 'policy')}  \n"
            f"**Intent:** {intent}  \n"
            f"**Latency:** {response['latency_ms']} ms  \n"
            f"**Query ID:** {response['query_id']}"
        )
        if response.get("hits"):
            st.markdown("**Retrieved chunks**")
            for hit in response["hits"]:
                st.markdown(
                    f"**{hit['score']:.3f}** · {hit.get('heading', '')} · "
                    f"{hit.get('source_title', '')}"
                )
                st.caption(hit.get("text", "")[:600])
                st.caption(f"Citation: {hit.get('source_url', '')}")
                st.divider()
        st.markdown("**Stage artifacts**")
        for label, path in response["artifacts"].items():
            try:
                st.markdown(f"**{label}** — `{path}`")
                st.json(read_json(Path(path)))
            except Exception as exc:  # noqa: BLE001
                st.caption(f"Could not read {path}: {exc}")

    # Wire up follow-up chips via session state through a hidden mechanism:
    # Streamlit buttons cannot be inside unsafe HTML, so render real buttons.
    if route == "answer":
        scheme = SCHEME_BY_ID.get(response.get("scheme", ""))
        chips = FOLLOWUPS.get(intent, [])
        if scheme and chips:
            cols = st.columns(len(chips))
            for col, chip in zip(cols, chips):
                if col.button(chip, key=f"fu_{response['query_id']}_{chip}"):
                    topic = CHIP_TOPIC.get(chip, chip.lower())
                    st.session_state.pending_prompt = f"What is the {topic} of {scheme.name}?"
                    st.rerun()


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

# ---------- session state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = ""

# ---------- welcome state ----------
if not st.session_state.messages:
    st.markdown(
        '<div class="welcome"><h2>Ask about any mutual fund</h2>'
        '<p>Factual answers from official fund pages, with one citation per answer.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="starter-chips">', unsafe_allow_html=True)
    cols = st.columns(len(_STARTERS))
    for col, label in zip(cols, _STARTERS):
        if col.button(label, key=f"starter_{label}"):
            topic = CHIP_TOPIC[label]
            st.session_state.pending_prompt = f"What is the {topic} of HDFC Large Cap Fund Direct Growth?"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- thread ----------
st.markdown('<div class="thread" id="thread">', unsafe_allow_html=True)
for message in st.session_state.messages:
    if message["role"] == "user":
        render_user(message["content"])
    else:
        render_assistant(message["response"])
st.markdown('<div id="thread-bottom"></div></div>', unsafe_allow_html=True)

# ---------- input ----------
prompt = st.chat_input("Ask about expense ratio, exit load, SIP…")
if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = ""

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_user(prompt)

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
    render_assistant(response)
    st.session_state.messages.append({"role": "assistant", "response": response})

# scroll to bottom
components.html(
    "<script>window.parent.document.getElementById('thread-bottom').scrollIntoView({behavior:'smooth',block:'end'});</script>",
    height=0,
)

st.markdown('<div class="composer-caption">Facts from public fund pages. Not investment advice.</div>',
            unsafe_allow_html=True)