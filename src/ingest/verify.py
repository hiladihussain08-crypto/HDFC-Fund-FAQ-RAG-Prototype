"""Phase 3 acceptance check: prove the index is queryable and complete.

Runs after indexing and writes ``artifacts/04_vectordb/phase3_report.json``:

1. Chroma count equals the chunk count.
2. Every chunk id the embedder produced is present in the collection.
3. Vectors are ``config.embedding.expected_dim`` wide.
4. The collection reports the configured distance space (cosine by default).
5. Every stored row still carries its ``source_url`` citation.
6. A sanity query (``verify.phase3.query``) puts the expected fact chunk in
   the top ``top_k`` hits.

Any failed check aborts the phase instead of leaving a half-valid index.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from src.config import AppConfig, load_config
from src.embedding import embed_query
from src.ingest.embed import read_embeddings
from src.ingest.index import _open_client
from src.utils import read_jsonl, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORT_FILE = "phase3_report.json"


def _check(name: str, passed: bool, detail: str) -> dict:
    return {"check": name, "passed": bool(passed), "detail": detail}


def verify_index(config: AppConfig | None = None) -> dict:
    config = config or load_config()
    check_cfg = config.phase3_check
    chunks = read_jsonl(config.chunks_dir / "chunks.jsonl")
    embeddings = read_embeddings(config)
    collection = _open_client(config).get_collection(config.chroma.collection)
    space = str((collection.metadata or {}).get("hnsw:space", ""))

    checks: list[dict] = []

    count = collection.count()
    checks.append(
        _check(
            "collection_count_equals_chunks",
            count == len(chunks),
            f"chroma={count} chunks={len(chunks)}",
        )
    )

    stored = collection.get(ids=embeddings["ids"], include=["metadatas"])
    stored_ids = set(stored.get("ids") or [])
    missing = [cid for cid in embeddings["ids"] if cid not in stored_ids]
    checks.append(
        _check(
            "every_embedded_chunk_indexed",
            not missing,
            f"missing={len(missing)}" + (f" e.g. {missing[:2]}" if missing else ""),
        )
    )

    expected_dim = config.embedding.expected_dim
    dims = {len(vector) for vector in embeddings["vectors"]}
    checks.append(
        _check(
            "vectors_are_expected_dim",
            dims == {expected_dim},
            f"expected={expected_dim} found={sorted(dims)}",
        )
    )

    checks.append(
        _check(
            "distance_space_is_config",
            space == config.chroma.space,
            f"collection={space or 'unset'} config={config.chroma.space}",
        )
    )

    metadatas = stored.get("metadatas") or []
    without_url = [
        meta.get("chunk_id", "?")
        for meta in metadatas
        if not str(meta.get("source_url", "")).startswith("https://")
    ]
    checks.append(
        _check(
            "every_row_keeps_citation",
            not without_url,
            f"rows_without_url={len(without_url)}",
        )
    )

    hits = _sanity_query(config, collection, check_cfg.query, check_cfg.top_k)
    matched = [
        hit
        for hit in hits
        if hit["scheme"] == check_cfg.expect_scheme
        and check_cfg.expect_heading_contains in hit["heading"].lower()
    ]
    checks.append(
        _check(
            "sanity_query_hits_expected_chunk",
            bool(matched),
            f"query={check_cfg.query!r} top{check_cfg.top_k}="
            f"{[hit['chunk_id'] for hit in hits]}",
        )
    )

    passed = all(check["passed"] for check in checks)
    report = {
        "phase": "03_embed_and_index",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collection": config.chroma.collection,
        "embedding_model": config.embedding.model,
        "space": config.chroma.space,
        "dim": expected_dim,
        "chunks": len(chunks),
        "collection_count": count,
        "passed": passed,
        "checks": checks,
        "sanity_query": {
            "query": check_cfg.query,
            "top_k": check_cfg.top_k,
            "hits": hits,
        },
    }
    write_json(config.vectordb_dir / REPORT_FILE, report)

    for check in checks:
        print(f"  {'PASS' if check['passed'] else 'FAIL'} {check['check']}: {check['detail']}")
    print(f"Phase 3 report -> {config.vectordb_dir / REPORT_FILE}")

    if not passed:
        failed = [check["check"] for check in checks if not check["passed"]]
        raise RuntimeError(f"Phase 3 acceptance failed: {failed}")
    return report


def _sanity_query(config: AppConfig, collection, query: str, top_k: int) -> list[dict]:
    result = collection.query(
        query_embeddings=[embed_query(query, config)],
        n_results=top_k,
        include=["metadatas", "distances"],
    )
    ids = (result.get("ids") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return [
        {
            "chunk_id": chunk_id,
            "score": round(1.0 - float(distance), 4),
            "scheme": str(meta.get("scheme", "")),
            "heading": str(meta.get("heading", "")),
            "url": str(meta.get("source_url", "")),
        }
        for chunk_id, meta, distance in zip(ids, metadatas, distances)
    ]


def main() -> None:
    verify_index()


if __name__ == "__main__":
    main()
