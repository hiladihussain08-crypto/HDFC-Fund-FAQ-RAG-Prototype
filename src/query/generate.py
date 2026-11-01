"""Phase 7 (generate): LLM answer from retrieved context only.

The LLM never chooses the citation; this module attaches exactly one URL from
the retrieved hits and appends the last-updated line.  If the LLM is missing or
unavailable, a deterministic extractive answer keeps the demo working.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.config import AppConfig
from src.query.guard import detect_advice
from src.query.llm import call_llm
from src.utils import (
    clean_text,
    one_line,
    split_sentences,
    strip_urls,
    truncate_sentences,
)

SYSTEM_PROMPT = """You are the Groww Mutual Fund FAQ Assistant, a facts-only retrieval assistant for four HDFC Mutual Fund schemes and Groww/SEBI/AMFI help pages.

RULES
1. Identify the exact fact the user asks: expense ratio, exit load, minimum SIP or lump-sum, lock-in, riskometer, benchmark, fund manager, AUM, category, launch date, stamp duty, or how to download a statement.
2. Answer in at most 3 short sentences. No bullets, no markdown, no headings.
3. Use ONLY the facts in CONTEXT. Never guess, infer, or use outside knowledge.
4. Never give investment advice, recommendations, rankings, or opinions.
5. Never compute, compare, or quote returns, CAGR, NAV, or performance.
6. If CONTEXT does not contain the exact fact, output exactly: NOT_IN_CONTEXT
7. Do not include URLs, source lines, or last-updated lines. The application adds exactly one citation.
8. If the question names a scheme, use only that scheme's facts. Never mix schemes.
9. For statement questions, give the concrete steps found in CONTEXT.
"""

INTENT_HEADINGS = {
    "expense_ratio": ("expense ratio", "expense"),
    "exit_load": ("exit load",),
    "min_sip": ("minimum sip", "sip"),
    "min_investment": ("minimum investment", "minimum additional", "lump-sum"),
    "lock_in": ("lock-in", "lock in"),
    "riskometer": ("riskometer", "risk"),
    "benchmark": ("benchmark",),
    "fund_manager": ("fund manager",),
    "fund_house": ("fund house",),
    "aum": ("assets under management", "aum"),
    "category": ("category",),
    "launch_date": ("launch date",),
    "stamp_duty": ("stamp duty",),
    "statement": ("statement", "report", "capital gain"),
}


@dataclass
class GenerationResult:
    answer: str
    mode: str
    citation_url: str
    citation_title: str
    last_updated: str
    system_prompt: str
    user_prompt: str
    context_pack: list[dict[str, Any]] = field(default_factory=list)
    raw_completion: str = ""
    provider: str = ""
    model: str = ""
    error: str | None = None
    used_chunk_id: str = ""
    hit: dict[str, Any] | None = None


def _context_pack(hits: list[dict[str, Any]], limit_chars: int = 1100) -> list[dict[str, Any]]:
    pack: list[dict[str, Any]] = []
    for index, hit in enumerate(hits, start=1):
        text = clean_text(hit.get("text", ""))
        if len(text) > limit_chars:
            text = text[:limit_chars].rsplit(" ", 1)[0] + " ..."
        pack.append(
            {
                "index": index,
                "chunk_id": hit.get("chunk_id", ""),
                "source_title": hit.get("source_title", ""),
                "source_url": hit.get("source_url", ""),
                "heading": hit.get("heading", ""),
                "kind": hit.get("kind", ""),
                "score": hit.get("score", 0.0),
                "text": text,
            }
        )
    return pack


def _build_user_prompt(question: str, pack: list[dict[str, Any]]) -> str:
    lines = [f"QUESTION: {question}", "", "CONTEXT:"]
    for item in pack:
        lines.append(
            f"[{item['index']}] {item['source_title']} | {item['heading']} "
            f"(similarity {item['score']:.2f})"
        )
        lines.append(item["text"])
        lines.append("")
    lines.append("ANSWER (max 3 sentences, facts from CONTEXT only):")
    return "\n".join(lines)


def _clean_completion(text: str, max_sentences: int) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    text = re.sub(r"(?im)^\s*(answer|final answer)\s*:\s*", "", text)
    text = re.sub(
        r"(?im)^\s*(source|last updated from sources|citation)\s*:.*$", "", text
    )
    text = strip_urls(text)
    text = re.sub(r"\s+", " ", text).strip().strip('"').strip()
    return truncate_sentences(text, max_sentences)


def _is_refusal(answer: str) -> bool:
    lowered = answer.strip().lower()
    return lowered == "not_in_context" or lowered.startswith("not_in_context")


def _intent_heading_match(hit: dict[str, Any], intent: str) -> bool:
    heading = (hit.get("heading") or "").lower()
    text = (hit.get("text") or "").lower()
    for needle in INTENT_HEADINGS.get(intent, ()):
        if needle in heading or needle in text[:160]:
            return True
    return False


def pick_citation(
    hits: list[dict[str, Any]], intent: str, question: str
) -> dict[str, Any] | None:
    if not hits:
        return None
    fact_hits = [
        hit
        for hit in hits
        if hit.get("kind") == "fact" and _intent_heading_match(hit, intent)
    ]
    if fact_hits:
        return fact_hits[0]
    if intent == "statement":
        help_hits = [
            hit
            for hit in hits
            if hit.get("doc_type") in {"help", "blog", "rta", "regulator"}
        ]
        if help_hits:
            return help_hits[0]
    return hits[0]


def _best_sentences(
    text: str, question: str, limit: int, min_score: float = 0.0
) -> list[str]:
    stop = {
        "what", "which", "how", "is", "the", "of", "for", "a", "an", "to", "in",
        "do", "does", "i", "my", "can", "you", "and", "or", "on", "it", "this",
        "that", "hdfc", "fund", "scheme", "please", "tell", "me", "about",
    }
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", question.lower())
        if token not in stop and len(token) > 2
    }

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    sentences: list[str] = []
    for line in lines:
        parts = split_sentences(line)
        sentences.extend(parts or [line])

    scored: list[tuple[float, int, str]] = []
    for index, sentence in enumerate(sentences):
        lowered = sentence.lower()
        score = sum(1 for token in tokens if token in lowered)
        if score >= min_score:
            scored.append((score, index, sentence))
    if not scored:
        return sentences[:limit]
    best = sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]
    best.sort(key=lambda item: item[1])
    return [sentence for _, _, sentence in best]


def _statement_steps(text: str, max_sentences: int) -> str:
    """Turn a help-page walkthrough into one compact, actionable sentence."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    steps: list[str] = []
    for line in lines:
        match = re.match(
            r"(?i)^(?:step\s*\d+\s*[:.)-]?\s*|\d+[.)]\s*|[-•]\s*)(.+)$", line
        )
        if match:
            steps.append(match.group(1).strip())
    if not steps:
        steps = [line for line in lines if 8 <= len(line) <= 240][:max_sentences]
    cleaned: list[str] = []
    for step in steps:
        # A step line often carries a trailing explanatory sentence; keep the
        # instruction itself so the compact answer stays actionable.
        step = re.split(r"(?<=[.!?])\s+", step.strip())[0]
        step = re.sub(
            r"(?i)^(now|after that|next|then)\s*[,:]?\s+", "", step
        ).rstrip(" .")
        if step:
            cleaned.append(step)
    steps = cleaned[:max_sentences]
    if not steps:
        return ""
    answer = "; then ".join(steps)
    return answer[:1].upper() + answer[1:] + "."


def build_extractive(
    hits: list[dict[str, Any]], question: str, intent: str, max_sentences: int
) -> tuple[str, dict[str, Any] | None]:
    """Deterministic fallback: use the fact chunk's authored answer, else the
    most query-relevant sentences from the top chunk."""

    if intent == "statement":
        for hit in hits:
            if hit.get("doc_type") in {
                "help",
                "blog",
                "rta",
                "regulator",
                "amc_education",
            }:
                answer = _statement_steps(hit.get("text", ""), max_sentences)
                if answer:
                    return answer, hit

    for hit in hits:
        if hit.get("kind") == "fact" and hit.get("answer") and _intent_heading_match(
            hit, intent
        ):
            answer = truncate_sentences(hit["answer"], max_sentences)
            return answer, hit

    for hit in hits:
        if hit.get("kind") == "fact" and hit.get("answer"):
            answer = truncate_sentences(hit["answer"], max_sentences)
            return answer, hit

    for hit in hits[:3]:
        sentences = _best_sentences(hit.get("text", ""), question, max_sentences)
        if sentences:
            answer = truncate_sentences(" ".join(sentences), max_sentences)
            if answer:
                return answer, hit
    return "", None


def _last_updated(hits: list[dict[str, Any]]) -> str:
    stamps = [hit.get("fetched_at", "") for hit in hits if hit.get("fetched_at")]
    if not stamps:
        return ""
    return max(stamps)[:10]


def generate_from_context(
    question: str,
    hits: list[dict[str, Any]],
    config: AppConfig,
    intent: str = "other",
) -> GenerationResult:
    pack = _context_pack(hits)
    user_prompt = _build_user_prompt(question, pack)

    llm = call_llm(SYSTEM_PROMPT, user_prompt, config.llm)
    answer = _clean_completion(llm.text, config.policy.max_sentences)
    mode = f"llm:{llm.provider}:{llm.model}" if answer and not _is_refusal(answer) else ""

    error = llm.error
    if not answer or _is_refusal(answer) or detect_advice(answer):
        if not config.llm.fallback_to_extractive:
            return GenerationResult(
                answer="",
                mode="llm_failed",
                citation_url="",
                citation_title="",
                last_updated="",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                context_pack=pack,
                raw_completion=llm.text,
                provider=llm.provider,
                model=llm.model,
                error=error or "empty_or_unsafe_completion",
            )
        extractive, hit = build_extractive(
            hits, question, intent, config.policy.max_sentences
        )
        if not extractive:
            return GenerationResult(
                answer="",
                mode="no_answer",
                citation_url="",
                citation_title="",
                last_updated="",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                context_pack=pack,
                raw_completion=llm.text,
                provider=llm.provider,
                model=llm.model,
                error=error or "no_extractive_answer",
            )
        answer = extractive
        mode = "extractive_fallback"
        citation = hit or pick_citation(hits, intent, question)
        error = error or "llm_unavailable_or_unsafe"
    else:
        citation = pick_citation(hits, intent, question)

    if citation is None:
        return GenerationResult(
            answer="",
            mode="no_citation",
            citation_url="",
            citation_title="",
            last_updated="",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            context_pack=pack,
            raw_completion=llm.text,
            provider=llm.provider,
            model=llm.model,
            error="no_citation_in_hits",
        )

    return GenerationResult(
        answer=answer,
        mode=mode or "llm",
        citation_url=citation["source_url"],
        citation_title=citation.get("source_title", ""),
        last_updated=_last_updated(hits),
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        context_pack=pack,
        raw_completion=llm.text,
        provider=llm.provider,
        model=llm.model,
        error=error,
        used_chunk_id=citation.get("chunk_id", ""),
        hit=citation,
    )
