"""Phase 7 (retrieve): query the same Chroma collection with the same model.

Every setting (embedding model, collection, distance space, top-k, similarity
floor, scheme filter) is read from ``config.yaml``. The collection is opened
read-only and its stored metadata is checked against the config before any
query runs, so a stale index fails loudly instead of returning junk.

Output per question: ``artifacts/05_retrieval/<query_id>.json`` with
``question, query_embedding_id, top_chunks[{chunk_id, score, url, section,
text_snippet}]`` plus the full hit list. A golden-set run writes
``artifacts/05_retrieval/phase7_report.json``.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import asdict
from typing import Any

from src.config import AppConfig, load_config
from src.embedding import embed_query
from src.schemes import Scheme, detect_scheme
from src.utils import read_jsonl, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Golden set used by the phase-7 acceptance run. Each entry names one or more
# acceptable chunk-id prefixes; a hit counts if any of them lands in the top 3.
GOLDEN_SET: list[dict[str, Any]] = [
    {
        "question": "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
        "expected": ["groww-large-cap::fact::expense-ratio"],
    },
    {
        "question": "What is the expense ratio of HDFC ELSS Tax Saver Fund Direct Plan Growth?",
        "expected": ["groww-elss::fact::expense-ratio"],
    },
    {
        "question": "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
        "expected": ["groww-elss::fact::lock-in"],
    },
    {
        "question": "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
        "expected": ["groww-large-cap::fact::minimum-sip"],
    },
    {
        "question": "What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?",
        "expected": ["groww-mid-cap::fact::minimum-sip"],
    },
    {
        "question": "What is the exit load of HDFC Flexi Cap Direct Plan Growth?",
        "expected": ["groww-flexi-cap::fact::exit-load"],
    },
    {
        "question": "What is the benchmark of HDFC Mid Cap Fund Direct Growth?",
        "expected": ["groww-mid-cap::fact::benchmark"],
    },
    {
        "question": "What is the riskometer level of HDFC ELSS Tax Saver Fund?",
        "expected": ["groww-elss::fact::riskometer"],
    },
    {
        "question": "Which AMC manages HDFC Large Cap Fund Direct Growth?",
        "expected": ["groww-large-cap::fact::fund-house"],
    },
    {
        "question": "How do I download my capital gains statement?",
        "expected": ["groww-learn-capital-gains", "groww-help", "groww-blog"],
    },
]


def _client(config: AppConfig):
    import chromadb

    return chromadb.PersistentClient(path=str(config.chroma.persist_dir))


def _collection(config: AppConfig):
    client = _client(config)
    collection = client.get_collection(name=config.chroma.collection)
    meta = collection.metadata or {}
    space = str(meta.get("hnsw:space", ""))
    model = str(meta.get("embedding_model", ""))
    if space != config.chroma.space:
        raise RuntimeError(
            f"Chroma space {space!r} != config {config.chroma.space!r}; "
            "re-run the index phase"
        )
    if model != config.embedding.model:
        raise RuntimeError(
            f"Chroma model {model!r} != config {config.embedding.model!r}; "
            "re-run the index phase"
        )
    chunks = read_jsonl(config.chunks_dir / "chunks.jsonl")
    if chunks and collection.count() != len(chunks):
        raise RuntimeError(
            f"Chroma count {collection.count()} != chunks {len(chunks)}; "
            "re-run the index phase"
        )
    return collection


def _score(distance: float, space: str) -> float:
    if space == "cosine":
        return max(0.0, min(1.0, 1.0 - float(distance)))
    if space == "l2":
        return 1.0 / (1.0 + float(distance))
    if space == "ip":
        return float(distance)
    return max(0.0, min(1.0, 1.0 - float(distance)))


def _query_embedding_id(question: str, config: AppConfig) -> str:
    digest = hashlib.sha1(
        f"{config.embedding.model}\x00{question.strip().lower()}".encode("utf-8")
    ).hexdigest()
    return f"qe-{digest[:12]}"


def collection_count(config: AppConfig) -> int:
    return _collection(config).count()


def retrieve(
    question: str,
    config: AppConfig | None = None,
    scheme: Scheme | None = None,
    k: int | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    config = config or load_config()
    k = k or config.retrieval.k
    space = config.chroma.space
    vector = embed_query(question, config)
    collection = _collection(config)

    if collection.count() == 0:
        return {
            "hits": [],
            "raw": [],
            "top_chunks": [],
            "count": 0,
            "query_embedding_id": _query_embedding_id(question, config),
        }

    where: dict[str, Any] | None = None
    clauses: list[dict[str, Any]] = []
    if scheme and config.retrieval.filter_by_scheme:
        clauses.append({"source_id": scheme.source_id})
    if category:
        clauses.append({"category": category})
    if len(clauses) == 1:
        where = clauses[0]
    elif len(clauses) > 1:
        where = {"$and": clauses}

    n_results = min(
        max(config.retrieval.candidate_k, k),
        max(collection.count(), 1),
    )

    result = collection.query(
        query_embeddings=[vector],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    raw: list[dict[str, Any]] = []
    for chunk_id, document, metadata, distance in zip(
        ids, documents, metadatas, distances
    ):
        metadata = metadata or {}
        score = _score(float(distance), space)
        raw.append(
            {
                "chunk_id": chunk_id,
                "score": round(score, 4),
                "distance": round(float(distance), 4),
                "text": document,
                "text_snippet": (document or "")[:240],
                "heading": metadata.get("heading", ""),
                "section": metadata.get("section", ""),
                "breadcrumb": metadata.get("breadcrumb", ""),
                "source_id": metadata.get("source_id", ""),
                "source_url": metadata.get("source_url", ""),
                "source_title": metadata.get("source_title", ""),
                "scheme": metadata.get("scheme", ""),
                "category": metadata.get("category", ""),
                "doc_type": metadata.get("doc_type", ""),
                "kind": metadata.get("kind", ""),
                "answer": metadata.get("answer", ""),
                "fetched_at": metadata.get("fetched_at", ""),
            }
        )

    raw.sort(key=lambda hit: hit["score"], reverse=True)
    hits = [hit for hit in raw if hit["score"] >= config.retrieval.min_score][:k]

    top_chunks = [
        {
            "chunk_id": hit["chunk_id"],
            "score": hit["score"],
            "url": hit["source_url"],
            "section": hit["section"] or hit["heading"],
            "text_snippet": hit["text_snippet"],
        }
        for hit in hits
    ]

    return {
        "hits": hits,
        "raw": raw,
        "top_chunks": top_chunks,
        "count": len(raw),
        "min_score": config.retrieval.min_score,
        "k": k,
        "where": where,
        "embedding_model": config.embedding.model,
        "collection": config.chroma.collection,
        "space": space,
        "query_embedding_id": _query_embedding_id(question, config),
        "scheme": asdict(scheme) if scheme else None,
    }


def run_golden_set(config: AppConfig | None = None) -> dict[str, Any]:
    """Phase-7 acceptance: does the right chunk land in the top 3?"""

    config = config or load_config()
    config.ensure_dirs()
    allowed = {
        row["url"].strip()
        for row in __import__("csv").DictReader(
            config.sources_file.open(encoding="utf-8-sig")
        )
    }
    results: list[dict[str, Any]] = []
    hits = 0
    for entry in GOLDEN_SET:
        question = entry["question"]
        expected = entry["expected"]
        result = retrieve(question, config, detect_scheme(question))
        top = result["hits"][:3]
        matched = [
            hit["chunk_id"]
            for hit in top
            if any(hit["chunk_id"].startswith(prefix) for prefix in expected)
        ]
        ok = bool(matched)
        hits += int(ok)
        citation_ok = all(
            hit["source_url"] in allowed for hit in top if hit.get("source_url")
        )
        results.append(
            {
                "question": question,
                "expected": expected,
                "top3": [hit["chunk_id"] for hit in top],
                "matched": matched,
                "passed": ok,
                "citation_urls_allowlisted": citation_ok,
                "scores": [hit["score"] for hit in top],
            }
        )

    hit_rate = hits / len(GOLDEN_SET) if GOLDEN_SET else 0.0
    citation_ok = all(item["citation_urls_allowlisted"] for item in results)
    passed = hit_rate >= 0.9 and citation_ok
    report = {
        "phase": "07_retrieval",
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collection": config.chroma.collection,
        "embedding_model": config.embedding.model,
        "space": config.chroma.space,
        "min_score": config.retrieval.min_score,
        "k": config.retrieval.k,
        "candidate_k": config.retrieval.candidate_k,
        "golden_questions": len(GOLDEN_SET),
        "top3_hits": hits,
        "hit_rate": round(hit_rate, 4),
        "citation_urls_allowlisted": citation_ok,
        "passed": passed,
        "results": results,
    }
    write_json(config.retrieval_dir / "phase7_report.json", report)
    for item in results:
        print(
            f"  {'PASS' if item['passed'] else 'FAIL'} "
            f"{item['question'][:48]:<48} -> {item['top3'][:1]}"
        )
    print(
        f"Phase 7 report -> {config.retrieval_dir / 'phase7_report.json'} "
        f"(hit_rate={hit_rate:.2%})"
    )
    if not passed:
        failed = [item["question"] for item in results if not item["passed"]]
        raise RuntimeError(f"Phase 7 retrieval acceptance failed: {failed}")
    return report


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Retrieve chunks for a question")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--k", type=int, default=None)
    parser.add_argument("--golden", action="store_true", help="run the golden set")
    args = parser.parse_args()

    config = load_config()
    if args.golden:
        run_golden_set(config)
        return
    if not args.question:
        parser.error("question is required unless --golden is given")
    result = retrieve(args.question, config, detect_scheme(args.question), args.k)
    print(json.dumps(result["hits"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
