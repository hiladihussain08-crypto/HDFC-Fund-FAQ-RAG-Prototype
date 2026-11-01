"""Query pipeline: guard -> retrieve -> generate -> persist one answer."""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.config import AppConfig, load_config
from src.query.generate import generate_from_context
from src.query.guard import (
    ANSWER,
    MISS,
    GuardResult,
    detect_intent,
    guard_question,
)
from src.query.retrieve import retrieve
from src.utils import read_jsonl, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FACT_INTENTS = {
    "expense_ratio",
    "exit_load",
    "min_sip",
    "min_investment",
    "lock_in",
    "riskometer",
    "benchmark",
    "fund_manager",
    "fund_house",
    "aum",
    "category",
    "launch_date",
    "stamp_duty",
}


def _source_catalog(config: AppConfig) -> dict[str, dict[str, str]]:
    """id -> {url, title, fetched_at} from sources.csv + loaded documents."""
    catalog: dict[str, dict[str, str]] = {}
    with config.sources_file.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            catalog[row["id"]] = {
                "url": row.get("url", ""),
                "title": row.get("title", ""),
                "fetched_at": "",
            }
    for document in read_jsonl(config.loaded_dir / "documents.jsonl"):
        entry = catalog.setdefault(
            document["id"],
            {
                "url": document.get("url", ""),
                "title": document.get("title", ""),
                "fetched_at": "",
            },
        )
        entry["fetched_at"] = document.get("fetched_at", "")
        entry["url"] = entry["url"] or document.get("url", "")
        entry["title"] = entry["title"] or document.get("title", "")
    return catalog


def _new_query_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{uuid4().hex[:6]}"


def _policy_last_updated(info: dict[str, str], config: AppConfig) -> str:
    stamp = (info.get("fetched_at") or "")[:10]
    if stamp:
        return f"{config.policy.last_updated_prefix}{stamp}"
    return config.policy.refusal_last_updated


def _compose(
    route: str,
    reason: str,
    question: str,
    answer: str,
    citation_url: str,
    citation_title: str,
    last_updated: str,
    *,
    scheme: str = "",
    intent: str = "other",
    hits: list[dict[str, Any]] | None = None,
    generation: dict[str, Any] | None = None,
    config: AppConfig,
) -> dict[str, Any]:
    prefix = config.policy.last_updated_prefix
    last_updated_line = (
        last_updated
        if last_updated.startswith(prefix)
        else f"{prefix}{last_updated}"
    )
    display = f"{answer}\n\nSource: {citation_url}\n{last_updated_line}"
    return {
        "route": route,
        "reason": reason,
        "question": question,
        "scheme": scheme,
        "intent": intent,
        "answer": answer,
        "citation_url": citation_url,
        "citation_title": citation_title,
        "last_updated": last_updated_line,
        "display_answer": display,
        "hits": hits or [],
        "generation": generation or {},
        "disclaimer": config.ui.disclaimer,
    }


def answer_question(
    question: str,
    config: AppConfig | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    config = config or load_config()
    config.ensure_dirs()
    started = time.perf_counter()
    query_id = _new_query_id()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    guard = guard_question(question, config)
    catalog = _source_catalog(config)

    retrieval_artifact: dict[str, Any] = {
        "query_id": query_id,
        "timestamp": timestamp,
        "question": guard.log_question,
        "route": guard.route,
        "reason": guard.reason,
        "scheme": guard.scheme.source_id if guard.scheme else "",
        "intent": guard.intent,
        "k": config.retrieval.k,
        "min_score": config.retrieval.min_score,
        "embedding_model": config.embedding.model,
        "collection": config.chroma.collection,
        "hits": [],
        "raw": [],
        "retrieval_skipped": not guard.needs_retrieval,
    }

    # ----- non-retrieval routes: advice / returns / PII ----------------------
    if guard.route != ANSWER:
        info = catalog.get(guard.citation_source_id, {})
        response = _compose(
            guard.route,
            guard.reason,
            guard.log_question,
            guard.message,
            info.get("url", ""),
            info.get("title", ""),
            _policy_last_updated(info, config),
            scheme=guard.scheme.source_id if guard.scheme else "",
            intent=guard.intent,
            config=config,
        )
        response["query_id"] = query_id
        response["timestamp"] = timestamp
        response["guard"] = {
            "route": guard.route,
            "reason": guard.reason,
            "pii_types": list(guard.pii_types),
        }
        response["latency_ms"] = int((time.perf_counter() - started) * 1000)
        response["artifacts"] = {
            "retrieval": str(config.retrieval_dir / f"{query_id}.json"),
            "generation": str(config.generation_dir / f"{query_id}.json"),
        }

        generation_artifact = {
            "query_id": query_id,
            "timestamp": timestamp,
            "question": guard.log_question,
            "route": guard.route,
            "reason": guard.reason,
            "mode": "policy_response",
            "system_prompt": "",
            "user_prompt": "",
            "context_pack": [],
            "raw_completion": "",
            "answer": guard.message,
            "citation_url": response["citation_url"],
            "last_updated": response["last_updated"],
            "provider": "",
            "model": "",
            "error": "",
            "pii_redacted": bool(guard.pii_types),
        }
        if persist:
            write_json(config.retrieval_dir / f"{query_id}.json", retrieval_artifact)
            write_json(
                config.generation_dir / f"{query_id}.json", generation_artifact
            )
        return response

    # ----- factual route: retrieve -----------------------------------------
    # Statement how-tos live on help/blog/regulator pages, not on a scheme
    # page, so do not restrict retrieval to the named scheme.
    result = retrieve(
        question,
        config,
        None if guard.intent == "statement" else guard.scheme,
    )
    retrieval_artifact.update(
        {
            "query_embedding_id": result.get("query_embedding_id", ""),
            "hits": result["hits"],
            "raw": result["raw"],
            "top_chunks": result.get("top_chunks", []),
            "collection_count": result.get("count", 0),
            "where": result.get("where"),
        }
    )

    hits = result["hits"]

    # Statement questions must land on a help/blog/regulator/RTA page.
    if guard.intent == "statement":
        statement_hits = [
            hit
            for hit in hits
            if hit.get("doc_type") in {"help", "blog", "rta", "regulator", "amc_education"}
            or "statement" in (hit.get("text", "").lower())
        ]
        hits = statement_hits

    # A named fact must have a matching fact chunk in the top hits.
    if hits and guard.intent in FACT_INTENTS:
        from src.query.generate import _intent_heading_match

        if not any(_intent_heading_match(hit, guard.intent) for hit in hits[:3]):
            hits = []

    if not hits:
        info = catalog.get("groww-amc-hdfc", {})
        response = _compose(
            MISS,
            "no_relevant_hit",
            guard.log_question,
            (
                "I don't have that fact in the official pages I loaded. "
                "I cover these HDFC schemes: HDFC Large Cap Fund, HDFC Flexi Cap Fund, "
                "HDFC ELSS Tax Saver Fund, and HDFC Mid Cap Fund."
            ),
            info.get("url", ""),
            info.get("title", ""),
            _policy_last_updated(info, config),
            scheme=guard.scheme.source_id if guard.scheme else "",
            intent=guard.intent,
            config=config,
        )
        response["query_id"] = query_id
        response["timestamp"] = timestamp
        response["guard"] = {"route": guard.route, "reason": "no_relevant_hit"}
        response["latency_ms"] = int((time.perf_counter() - started) * 1000)
        response["artifacts"] = {
            "retrieval": str(config.retrieval_dir / f"{query_id}.json"),
            "generation": str(config.generation_dir / f"{query_id}.json"),
        }
        if persist:
            write_json(config.retrieval_dir / f"{query_id}.json", retrieval_artifact)
            write_json(
                config.generation_dir / f"{query_id}.json",
                {
                    "query_id": query_id,
                    "timestamp": timestamp,
                    "question": guard.log_question,
                    "route": MISS,
                    "reason": "no_relevant_hit",
                    "mode": "no_answer",
                    "system_prompt": "",
                    "user_prompt": "",
                    "context_pack": [],
                    "raw_completion": "",
                    "answer": response["answer"],
                    "citation_url": response["citation_url"],
                    "last_updated": response["last_updated"],
                    "provider": config.llm.provider,
                    "model": config.llm.model,
                    "error": "no_relevant_hit",
                },
            )
        return response

    # ----- generate ---------------------------------------------------------
    generation = generate_from_context(
        question, hits, config, intent=guard.intent or detect_intent(question)
    )

    if not generation.answer:
        info = catalog.get("groww-amc-hdfc", {})
        response = _compose(
            MISS,
            "generation_failed",
            guard.log_question,
            (
                "I found related official pages but could not extract a reliable "
                "answer. Please try rephrasing the question or ask about one of the "
                "covered HDFC schemes."
            ),
            info.get("url", ""),
            info.get("title", ""),
            _policy_last_updated(info, config),
            scheme=guard.scheme.source_id if guard.scheme else "",
            intent=guard.intent,
            config=config,
        )
    else:
        response = _compose(
            ANSWER,
            "factual",
            guard.log_question,
            generation.answer,
            generation.citation_url,
            generation.citation_title,
            generation.last_updated,
            scheme=guard.scheme.source_id if guard.scheme else "",
            intent=guard.intent,
            hits=hits,
            generation={
                "mode": generation.mode,
                "provider": generation.provider,
                "model": generation.model,
                "error": generation.error,
                "used_chunk_id": generation.used_chunk_id,
            },
            config=config,
        )

    response["query_id"] = query_id
    response["timestamp"] = timestamp
    response["guard"] = {
        "route": guard.route,
        "reason": guard.reason,
        "statement": guard.statement,
    }
    response["latency_ms"] = int((time.perf_counter() - started) * 1000)
    response["artifacts"] = {
        "retrieval": str(config.retrieval_dir / f"{query_id}.json"),
        "generation": str(config.generation_dir / f"{query_id}.json"),
    }

    if persist:
        write_json(config.retrieval_dir / f"{query_id}.json", retrieval_artifact)
        write_json(
            config.generation_dir / f"{query_id}.json",
            {
                "query_id": query_id,
                "timestamp": timestamp,
                "question": guard.log_question,
                "route": response["route"],
                "reason": response["reason"],
                "mode": generation.mode,
                "system_prompt": generation.system_prompt,
                "user_prompt": generation.user_prompt,
                "context_pack": generation.context_pack,
                "raw_completion": generation.raw_completion,
                "answer": generation.answer,
                "citation_url": generation.citation_url,
                "last_updated": generation.last_updated,
                "provider": generation.provider,
                "model": generation.model,
                "error": generation.error,
                "used_chunk_id": generation.used_chunk_id,
            },
        )
    return response


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Ask the HDFC MF FAQ assistant")
    parser.add_argument("question")
    parser.add_argument("--json", action="store_true", help="print full JSON")
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()

    response = answer_question(
        args.question, persist=not args.no_persist
    )
    if args.json:
        print(json.dumps(response, indent=2, ensure_ascii=False))
    else:
        print(response["display_answer"])
        print(f"\n[route={response['route']} mode={response['generation'].get('mode', 'policy')}]")


if __name__ == "__main__":
    main()
