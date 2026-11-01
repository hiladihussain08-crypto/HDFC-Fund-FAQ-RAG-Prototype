"""Phase 4 (chunk): structure-aware chunks from loaded documents.

Scheme pages get one self-contained fact strip per canonical fact (expense
ratio, exit load, SIP, lock-in, riskometer, benchmark, ...), so a value is
never cut in half. Remaining page text is split on headings and, if still
long, by the strategy in ``config.chunking.strategy``.

Output:
  artifacts/02_chunks/chunks.jsonl
  artifacts/02_chunks/chunks_summary.csv
  artifacts/02_chunks/phase4_report.json
"""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime, timezone
from typing import Any

from src.config import AppConfig, load_config
from src.embedding import get_model
from src.schemes import SCHEME_BY_ID
from src.utils import (
    clean_text,
    one_line,
    read_jsonl,
    short_hash,
    slugify,
    split_sentences,
    write_json,
    write_jsonl,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCHEME_BODY_TOPIC_RE = re.compile(
    r"(expense|exit load|sip|minimum|lock.?in|risk|benchmark|statement|"
    r"capital gain|tax|fund manager|aum|asset under|fund details|about|faq|"
    r"frequently asked|scheme details|investment objective|who should)",
    re.IGNORECASE,
)

SKIP_HEADING_RE = re.compile(
    r"(returns?|performance|cagr|nav\b|holdings|portfolio|peers?|similar funds|"
    r"compare|category average|trailing|since inception|turnover|sharpe|sortino|"
    r"alpha|beta|standard deviation|yield|dividend history|fund size|"
    r"expense ratio history|exit load history)",
    re.IGNORECASE,
)

# The AMC overview page mixes real AMC facts with Groww marketing, scheme
# return tables and a "how to invest" walkthrough.  Keep only the fact-bearing
# sections so the corpus cannot answer with performance or promo copy.
AMC_SECTION_ALLOW_RE = re.compile(
    r"^(hdfc mutual fund|key information about hdfc mutual fund|about amfi)$",
    re.IGNORECASE,
)

SKIP_SECTION_HEADING_RE = re.compile(
    r"^(disclaimer|dark|videos|scheme performance( indicator)?|"
    r"why invest with groww|how to invest in hdfc mf on groww|"
    r"view mutual funds from other amcs|final word)$",
    re.IGNORECASE,
)

MIN_SECTION_CHARS = 40
MIN_SCHEME_BODY_CHARS = 60
STRATEGIES = ("heading_then_recursive", "recursive", "fixed")


def _scheme_name(document: dict[str, Any]) -> str:
    facts = document.get("facts") or {}
    name = facts.get("scheme_name") or document.get("title") or document.get("id", "")
    scheme = SCHEME_BY_ID.get(document.get("scheme", ""))
    return scheme.name if scheme else name
RETURNS_TEXT_RE = re.compile(
    r"(\b1Y Returns\b|\bFund Performance\b|\bCAGR\b|\btrailing returns\b)",
    re.IGNORECASE,
)


def _fact(
    document: dict[str, Any],
    key: str,
    heading: str,
    text: str,
    answer: str,
    order: int,
) -> dict[str, Any]:
    cleaned = clean_text(text)
    return {
        "chunk_id": f"{document['id']}::fact::{key}",
        "source_id": document["id"],
        "source_url": document["url"],
        "source_title": document["title"],
        "scheme": document.get("scheme", ""),
        "category": document.get("category", ""),
        "doc_type": document.get("doc_type", ""),
        "heading": heading,
        "section": heading,
        "breadcrumb": f"{_scheme_name(document)} › {heading}",
        "text": cleaned,
        "answer": one_line(answer),
        "kind": "fact",
        "char_count": len(cleaned),
        "fetched_at": document.get("fetched_at", ""),
        "order": order,
    }


def scheme_fact_chunks(document: dict[str, Any]) -> list[dict[str, Any]]:
    facts = document.get("facts") or {}
    if not facts:
        return []
    name = facts.get("scheme_name") or document["title"]
    scheme = SCHEME_BY_ID.get(document.get("scheme", ""))
    if scheme:
        name = scheme.name

    chunks: list[dict[str, Any]] = []
    order = 0

    expense = facts.get("expense_ratio", "")
    base_expense = facts.get("base_expense_ratio", "")
    if expense:
        detail = f" Base expense ratio: {base_expense}." if base_expense else ""
        answer = f"The expense ratio of {name} is {expense}."
        if base_expense:
            answer = (
                f"The expense ratio of {name} is {expense} "
                f"(base expense ratio {base_expense})."
            )
        chunks.append(
            _fact(
                document,
                "expense-ratio",
                "Expense ratio",
                f"{name} — Expense ratio (TER): {expense}.{detail}",
                answer,
                order,
            )
        )
        order += 1

    exit_load = facts.get("exit_load", "")
    if exit_load:
        lowered = exit_load[0].lower() + exit_load[1:] if exit_load else exit_load
        if exit_load.strip().lower() in {"nil", "none", "no exit load"}:
            answer = f"{name} has no exit load."
        else:
            answer = f"For {name}, {lowered.rstrip('.')}."
        chunks.append(
            _fact(
                document,
                "exit-load",
                "Exit load",
                f"{name} — Exit load: {exit_load}.",
                answer,
                order,
            )
        )
        order += 1

    min_sip = facts.get("min_sip", "")
    if min_sip:
        chunks.append(
            _fact(
                document,
                "minimum-sip",
                "Minimum SIP",
                f"{name} — Minimum SIP investment: {min_sip} per instalment.",
                f"The minimum SIP amount for {name} is {min_sip}.",
                order,
            )
        )
        order += 1

    min_lumpsum = facts.get("min_lumpsum", "")
    if min_lumpsum:
        chunks.append(
            _fact(
                document,
                "minimum-lumpsum",
                "Minimum investment",
                f"{name} — Minimum lump-sum investment: {min_lumpsum}.",
                f"The minimum lump-sum investment for {name} is {min_lumpsum}.",
                order,
            )
        )
        order += 1

    lock_in = facts.get("lock_in", "")
    if lock_in:
        if lock_in.lower().startswith("no "):
            answer = f"{name} has no lock-in period."
        else:
            answer = f"The lock-in period for {name} is {lock_in}."
        chunks.append(
            _fact(
                document,
                "lock-in",
                "Lock-in",
                f"{name} — Lock-in: {lock_in}.",
                answer,
                order,
            )
        )
        order += 1

    risk = facts.get("riskometer", "")
    if risk:
        chunks.append(
            _fact(
                document,
                "riskometer",
                "Riskometer",
                f"{name} — Riskometer risk level: {risk}.",
                f"The riskometer level shown for {name} is {risk}.",
                order,
            )
        )
        order += 1

    benchmark = facts.get("benchmark", "")
    if benchmark:
        chunks.append(
            _fact(
                document,
                "benchmark",
                "Benchmark",
                f"{name} — Benchmark: {benchmark}.",
                f"The benchmark for {name} is {benchmark}.",
                order,
            )
        )
        order += 1

    manager = facts.get("fund_manager", "")
    if manager:
        chunks.append(
            _fact(
                document,
                "fund-manager",
                "Fund manager",
                f"{name} — Fund manager: {manager}.",
                f"The fund manager of {name} is {manager}.",
                order,
            )
        )
        order += 1

    aum = facts.get("aum", "")
    if aum:
        chunks.append(
            _fact(
                document,
                "aum",
                "Assets under management",
                f"{name} — Assets under management (AUM): {aum}.",
                f"The AUM of {name} is {aum}, as shown on its Groww page.",
                order,
            )
        )
        order += 1

    description = facts.get("description", "")
    if description:
        chunks.append(
            _fact(
                document,
                "objective",
                "Scheme objective",
                f"{name} — Scheme objective: {description}",
                f"{name} aims to {description[0].lower() + description[1:]}"
                if not description.lower().startswith("the scheme")
                else f"{description}",
                order,
            )
        )
        order += 1

    fund_house = facts.get("fund_house", "")
    if fund_house:
        chunks.append(
            _fact(
                document,
                "fund-house",
                "Fund house",
                f"{name} — Fund house: {fund_house}.",
                f"{name} is managed by {fund_house}.",
                order,
            )
        )
        order += 1

    category = facts.get("category", "")
    plan = facts.get("plan", "")
    if category:
        plan_text = f" Plan: {plan}." if plan else ""
        chunks.append(
            _fact(
                document,
                "category",
                "Category and plan",
                f"{name} — Category: {category}.{plan_text}",
                f"{name} is in the {category} category"
                + (f" ({plan} plan)." if plan else "."),
                order,
            )
        )
        order += 1

    launch_date = facts.get("launch_date", "")
    if launch_date:
        chunks.append(
            _fact(
                document,
                "launch-date",
                "Launch date",
                f"{name} — Launch date: {launch_date}.",
                f"{name} was launched on {launch_date}.",
                order,
            )
        )
        order += 1

    stamp_duty = facts.get("stamp_duty", "")
    if stamp_duty:
        chunks.append(
            _fact(
                document,
                "stamp-duty",
                "Stamp duty",
                f"{name} — Stamp duty: {stamp_duty}.",
                f"The stamp duty shown for {name} is {stamp_duty}.",
                order,
            )
        )
        order += 1

    min_additional = facts.get("min_additional", "")
    if min_additional:
        chunks.append(
            _fact(
                document,
                "minimum-additional",
                "Minimum additional investment",
                f"{name} — Minimum additional investment: {min_additional}.",
                f"The minimum additional investment for {name} is {min_additional}.",
                order,
            )
        )
        order += 1

    snapshot_parts = [
        f"Scheme: {name}",
        f"Fund house: {facts.get('fund_house')}" if facts.get("fund_house") else "",
        f"Category: {facts.get('category')}" if facts.get("category") else "",
        f"Plan: {facts.get('plan')}" if facts.get("plan") else "",
        f"Benchmark: {benchmark}" if benchmark else "",
        f"Expense ratio: {expense}" if expense else "",
        f"Exit load: {exit_load}" if exit_load else "",
        f"Minimum SIP: {min_sip}" if min_sip else "",
        f"Lock-in: {lock_in}" if lock_in else "",
        f"Riskometer: {risk}" if risk else "",
        f"Fund manager: {manager}" if manager else "",
        f"Launch date: {facts.get('launch_date')}" if facts.get("launch_date") else "",
        f"AUM: {aum}" if aum else "",
    ]
    snapshot = ". ".join(part for part in snapshot_parts if part) + "."
    chunks.append(
        _fact(
            document,
            "snapshot",
            "Scheme snapshot",
            snapshot,
            "",
            order,
        )
    )
    return chunks


def _split_long(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    units: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) <= max_chars:
            units.append(line)
        else:
            units.extend(split_sentences(line))

    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    for unit in units:
        addition = len(unit) + (1 if current else 0)
        if current and current_len + addition > max_chars:
            pieces.append("\n".join(current))
            # Keep a sentence-level overlap, never cut mid-sentence.
            overlap: list[str] = []
            overlap_len = 0
            for previous in reversed(current):
                if overlap_len + len(previous) > overlap_chars:
                    break
                overlap.insert(0, previous)
                overlap_len += len(previous) + 1
            current = overlap
            current_len = len("\n".join(current))
        current.append(unit)
        current_len += addition
    if current:
        pieces.append("\n".join(current))
    return [piece for piece in pieces if piece.strip()]


def body_chunks(
    document: dict[str, Any], max_chars: int, overlap_chars: int, min_chars: int
) -> list[dict[str, Any]]:
    is_scheme = document.get("doc_type") == "scheme_page"
    is_amc = document.get("doc_type") == "amc_overview"
    chunks: list[dict[str, Any]] = []
    order = 1000
    seen: set[str] = set()

    for section in document.get("sections") or []:
        heading = one_line(section.get("heading") or document["title"])
        text = clean_text(section.get("text") or "")
        if len(text) < min_chars or len(text) < MIN_SECTION_CHARS:
            continue
        if SKIP_SECTION_HEADING_RE.search(heading):
            continue
        if is_amc and not AMC_SECTION_ALLOW_RE.search(heading):
            continue
        if is_scheme:
            if SKIP_HEADING_RE.search(heading):
                continue
            if not SCHEME_BODY_TOPIC_RE.search(f"{heading}\n{text}"):
                continue
            if len(text) < MIN_SCHEME_BODY_CHARS:
                continue
        for piece in _split_long(text, max_chars, overlap_chars):
            key = short_hash(re.sub(r"\W+", "", piece.lower()))
            if key in seen:
                continue
            seen.add(key)
            chunk_id = f"{document['id']}::sec::{slugify(heading, 32)}::{order}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": document["id"],
                    "source_url": document["url"],
                    "source_title": document["title"],
                    "scheme": document.get("scheme", ""),
                    "category": document.get("category", ""),
                    "doc_type": document.get("doc_type", ""),
                    "heading": heading,
                    "section": heading,
                    "breadcrumb": heading,
                    "text": piece,
                    "answer": "",
                    "kind": "section",
                    "char_count": len(piece),
                    "fetched_at": document.get("fetched_at", ""),
                    "order": order,
                }
            )
            order += 1
    return chunks


def _fixed_windows(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Fixed character windows. Used only when strategy is ``fixed``."""

    if len(text) <= max_chars:
        return [text]
    step = max(1, max_chars - overlap_chars)
    pieces = []
    start = 0
    while start < len(text):
        pieces.append(text[start : start + max_chars].strip())
        start += step
    return [piece for piece in pieces if piece]


def _token_counts(texts: list[str], config: AppConfig) -> list[int]:
    tokenizer = get_model(config).tokenizer
    encoded = tokenizer(texts, add_special_tokens=False, truncation=False)
    return [len(ids) for ids in encoded["input_ids"]]


def _write_summary(path, chunks: list[dict[str, Any]]) -> int:
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for chunk in chunks:
        key = (
            chunk.get("source_id", ""),
            chunk.get("source_url", ""),
            chunk.get("section", ""),
            chunk.get("kind", ""),
        )
        row = groups.setdefault(
            key,
            {
                "source_id": key[0],
                "source_url": key[1],
                "section": key[2],
                "kind": key[3],
                "chunks": 0,
                "chars": 0,
            },
        )
        row["chunks"] += 1
        row["chars"] += int(chunk.get("char_count") or 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_id", "source_url", "section", "kind", "chunks", "chars"],
        )
        writer.writeheader()
        writer.writerows(groups.values())
    return len(groups)


def accept_chunks(config: AppConfig, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """PRD chunk acceptance. Writes the report, then raises on any failure."""

    required = (
        "chunk_id",
        "source_url",
        "scheme",
        "category",
        "section",
        "breadcrumb",
        "char_count",
        "token_count",
        "fetched_at",
    )
    checks: list[dict[str, Any]] = []

    missing_url = [c["chunk_id"] for c in chunks if not str(c.get("source_url", "")).startswith("https://")]
    checks.append(
        {
            "check": "every_chunk_has_source_url",
            "passed": not missing_url and bool(chunks),
            "detail": f"missing={len(missing_url)} chunks={len(chunks)}",
        }
    )

    optional = {"scheme", "category"}
    missing_meta = [
        c.get("chunk_id", "?")
        for c in chunks
        if any(key not in c for key in required)
        or any(c.get(key) in (None, "") for key in required if key not in optional)
    ]
    checks.append(
        {
            "check": "metadata_covers_every_chunk",
            "passed": not missing_meta,
            "detail": f"incomplete={len(missing_meta)}",
        }
    )

    oversized = [
        c["chunk_id"]
        for c in chunks
        if len(c.get("text", "")) > config.chunking.max_chars
        or int(c.get("char_count") or 0) != len(c.get("text", ""))
    ]
    checks.append(
        {
            "check": "no_chunk_over_max_chars",
            "passed": not oversized,
            "detail": f"max_chars={config.chunking.max_chars} over={len(oversized)}",
        }
    )

    over_tokens = [
        c["chunk_id"]
        for c in chunks
        if int(c.get("token_count") or 0) > config.chunking.max_tokens
    ]
    checks.append(
        {
            "check": "token_count_within_model_window",
            "passed": not over_tokens,
            "detail": f"max_tokens={config.chunking.max_tokens} over={len(over_tokens)}",
        }
    )

    bare_facts = []
    for chunk in chunks:
        if chunk.get("kind") != "fact":
            continue
        text = chunk.get("text", "")
        name = chunk.get("breadcrumb", "").split(" › ")[0]
        label = (chunk.get("section") or "").split()
        label_present = bool(label) and label[0] in text
        if not name or name not in text or not label_present:
            bare_facts.append(chunk.get("chunk_id"))
    checks.append(
        {
            "check": "fact_strips_are_self_contained",
            "passed": not bare_facts,
            "detail": f"bare={len(bare_facts)}",
        }
    )

    leaked = [c["chunk_id"] for c in chunks if RETURNS_TEXT_RE.search(c.get("text", ""))]
    checks.append(
        {
            "check": "no_returns_or_performance_tables",
            "passed": not leaked,
            "detail": f"leaked={len(leaked)}",
        }
    )

    passed = all(item["passed"] for item in checks)
    report = {
        "phase": "04_chunking",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "strategy": config.chunking.strategy,
        "max_chars": config.chunking.max_chars,
        "overlap_chars": config.chunking.overlap_chars,
        "max_tokens": config.chunking.max_tokens,
        "chunks": len(chunks),
        "passed": passed,
        "checks": checks,
    }
    write_json(config.chunks_dir / "phase4_report.json", report)
    for item in checks:
        print(f"  {'PASS' if item['passed'] else 'FAIL'} {item['check']}: {item['detail']}")
    if not passed:
        failed = [item["check"] for item in checks if not item["passed"]]
        raise RuntimeError(f"Phase 4 chunk acceptance failed: {failed}")
    return report


def chunk_documents(config: AppConfig | None = None) -> list[dict[str, Any]]:
    config = config or load_config()
    config.ensure_dirs()
    if config.chunking.strategy not in STRATEGIES:
        raise ValueError(
            f"Unknown chunking.strategy {config.chunking.strategy!r}. "
            f"Use one of {STRATEGIES}."
        )
    documents = read_jsonl(config.loaded_dir / "documents.jsonl")
    if not documents:
        raise FileNotFoundError(
            f"No documents in {config.loaded_dir}. Run the load phase first."
        )

    all_chunks: list[dict[str, Any]] = []
    per_source: dict[str, dict[str, int]] = {}
    for document in documents:
        facts = (
            scheme_fact_chunks(document)
            if document.get("doc_type") == "scheme_page"
            else []
        )
        body = body_chunks(
            document,
            config.chunking.max_chars,
            config.chunking.overlap_chars,
            config.chunking.min_chars,
        )
        if config.chunking.strategy == "fixed":
            body = _resplit(body, _fixed_windows, config)
        elif config.chunking.strategy == "recursive":
            body = _resplit(body, _split_long, config)
        chunks = facts + body
        all_chunks.extend(chunks)
        per_source[document["id"]] = {
            "facts": len(facts),
            "sections": len(body),
            "total": len(chunks),
        }
        print(f"ok   {document['id']:<32} {len(facts):>2} facts + {len(body):>3} sections")

    print(f"Counting tokens with {config.embedding.model}")
    counts = _token_counts([chunk["text"] for chunk in all_chunks], config)
    for chunk, count in zip(all_chunks, counts):
        chunk["token_count"] = count

    write_jsonl(config.chunks_dir / "chunks.jsonl", all_chunks)
    groups = _write_summary(config.chunks_dir / "chunks_summary.csv", all_chunks)
    manifest = {
        "phase": "04_chunking",
        "strategy": config.chunking.strategy,
        "max_chars": config.chunking.max_chars,
        "overlap_chars": config.chunking.overlap_chars,
        "min_chars": config.chunking.min_chars,
        "max_tokens": config.chunking.max_tokens,
        "chunks": len(all_chunks),
        "summary_rows": groups,
        "per_source": per_source,
    }
    write_json(config.chunks_dir / "manifest.json", manifest)
    print(f"\nWrote {len(all_chunks)} chunks, {groups} summary rows.")
    accept_chunks(config, all_chunks)
    return all_chunks


def _resplit(chunks: list[dict[str, Any]], splitter, config: AppConfig) -> list[dict[str, Any]]:
    """Re-cut section chunks when a non-default strategy is selected."""

    rewritten: list[dict[str, Any]] = []
    for chunk in chunks:
        pieces = splitter(
            chunk["text"], config.chunking.max_chars, config.chunking.overlap_chars
        )
        for index, piece in enumerate(pieces):
            if len(piece) < config.chunking.min_chars:
                continue
            clone = dict(chunk)
            clone["text"] = piece
            clone["char_count"] = len(piece)
            if len(pieces) > 1:
                clone["chunk_id"] = f"{chunk['chunk_id']}::{index}"
                clone["order"] = int(chunk.get("order", 0)) + index
            rewritten.append(clone)
    return rewritten


def main() -> None:
    chunk_documents()


if __name__ == "__main__":
    main()
