"""Phase 6 (vector DB): store chunk text, metadata, and vectors in ChromaDB.

No re-embedding happens here: vectors come from ``chunk_embeddings.npz``.
Persist directory, collection name, distance space, and upsert batch size
all come from ``config.yaml``.

Each record stores the chunk text and citation metadata next to its vector,
so a later query can return the fact and its URL without opening the npz.

Output: ``chroma_db/`` plus ``artifacts/04_vectordb/manifest.json``,
``phase6_report.json``, and a short ``stored_preview.json``.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

import numpy as np

from src.config import AppConfig, load_config
from src.ingest.embed import read_embeddings
from src.utils import read_jsonl, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_METADATA_KEYS = (
    "chunk_id",
    "source_id",
    "source_url",
    "source_title",
    "scheme",
    "doc_type",
    "heading",
    "section",
    "breadcrumb",
    "category",
    "kind",
    "answer",
    "fetched_at",
)


def _metadata(chunk: dict) -> dict:
    payload = {key: chunk.get(key, "") for key in _METADATA_KEYS}
    payload["order"] = int(chunk.get("order", 0))
    payload["token_count"] = int(chunk.get("token_count") or 0)
    payload["has_answer"] = bool(chunk.get("answer"))
    return payload


def _open_client(config: AppConfig):
    import chromadb

    return chromadb.PersistentClient(path=str(config.chroma.persist_dir))


def get_collection(config: AppConfig):
    """Return the live collection (query/verify reuse this)."""

    return _open_client(config).get_collection(config.chroma.collection)


def accept_store(config: AppConfig, chunks: list[dict], embeddings: dict, collection) -> dict:
    """Prove the collection actually holds the chunk text, citation, and vector."""

    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    stored = collection.get(
        ids=chunk_ids,
        include=["documents", "metadatas", "embeddings"],
    )
    stored_ids = list(stored.get("ids") or [])
    documents = list(stored.get("documents") or [])
    metadatas = list(stored.get("metadatas") or [])
    raw_vectors = stored.get("embeddings")
    vectors = [] if raw_vectors is None else [list(row) for row in raw_vectors]

    by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    expected = config.embedding.expected_dim
    required = ("chunk_id", "source_url", "scheme", "category", "section", "kind", "fetched_at")

    text_mismatch = [
        chunk_id
        for chunk_id, document in zip(stored_ids, documents)
        if document != by_id[chunk_id]["text"]
    ]
    missing_meta = []
    for chunk_id, meta in zip(stored_ids, metadatas):
        meta = meta or {}
        if any(key not in meta for key in required):
            missing_meta.append(chunk_id)
            continue
        if not str(meta.get("source_url", "")).startswith("https://"):
            missing_meta.append(chunk_id)
        elif meta.get("source_url") != by_id[chunk_id]["source_url"]:
            missing_meta.append(chunk_id)
    vector_mismatch = 0
    if len(vectors) != len(chunk_ids):
        vector_mismatch = len(chunk_ids)
    else:
        source = np.asarray(embeddings["vectors"], dtype=np.float32)
        saved = np.asarray(vectors, dtype=np.float32)
        if saved.shape != source.shape:
            vector_mismatch = len(chunk_ids)
        else:
            vector_mismatch = int(np.sum(~np.all(np.isclose(saved, source, atol=1e-5), axis=1)))

    space = str((collection.metadata or {}).get("hnsw:space", ""))
    model = str((collection.metadata or {}).get("embedding_model", ""))
    checks = [
        {
            "check": "collection_count_equals_chunks",
            "passed": collection.count() == len(chunks) and stored_ids == chunk_ids,
            "detail": f"chroma={collection.count()} chunks={len(chunks)}",
        },
        {
            "check": "document_text_round_trip",
            "passed": not text_mismatch and len(documents) == len(chunks),
            "detail": f"mismatched={len(text_mismatch)}",
        },
        {
            "check": "citation_metadata_stored",
            "passed": not missing_meta and len(metadatas) == len(chunks),
            "detail": f"incomplete={len(missing_meta)} fields={list(required)}",
        },
        {
            "check": "stored_vectors_match_embeddings",
            "passed": vector_mismatch == 0 and bool(vectors),
            "detail": f"mismatched={vector_mismatch} dim={expected}",
        },
        {
            "check": "store_settings_come_from_config",
            "passed": space == config.chroma.space and model == config.embedding.model,
            "detail": (
                f"space={space} model={model} "
                f"dir={config.chroma.persist_dir.name} collection={config.chroma.collection}"
            ),
        },
    ]
    passed = all(item["passed"] for item in checks)
    preview = []
    for chunk_id, document, meta in list(zip(stored_ids, documents, metadatas))[:3]:
        preview.append(
            {
                "chunk_id": chunk_id,
                "source_url": (meta or {}).get("source_url", ""),
                "section": (meta or {}).get("section", ""),
                "text": (document or "")[:180],
                "vector_dim": expected,
            }
        )
    report = {
        "phase": "06_vectordb",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collection": config.chroma.collection,
        "persist_dir": str(config.chroma.persist_dir.relative_to(config.project_root)),
        "space": config.chroma.space,
        "embedding_model": config.embedding.model,
        "count": collection.count(),
        "passed": passed,
        "checks": checks,
        "preview": preview,
    }
    write_json(config.vectordb_dir / "phase6_report.json", report)
    write_json(config.vectordb_dir / "stored_preview.json", {"records": preview})
    for item in checks:
        print(f"  {'PASS' if item['passed'] else 'FAIL'} {item['check']}: {item['detail']}")
    print(f"Phase 6 report -> {config.vectordb_dir / 'phase6_report.json'}")
    if not passed:
        failed = [item["check"] for item in checks if not item["passed"]]
        raise RuntimeError(f"Phase 6 vector-store acceptance failed: {failed}")
    return report


def index_chunks(
    config: AppConfig | None = None,
    reset: bool = True,
    verify: bool = True,
) -> dict:
    config = config or load_config()
    config.ensure_dirs()

    chunks = read_jsonl(config.chunks_dir / "chunks.jsonl")
    if not chunks:
        raise FileNotFoundError(
            f"No chunks in {config.chunks_dir}. Run the chunk phase first."
        )
    embeddings = read_embeddings(config)

    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    vector_ids = embeddings["ids"]
    if chunk_ids != vector_ids:
        missing = sorted(set(chunk_ids) - set(vector_ids))
        extra = sorted(set(vector_ids) - set(chunk_ids))
        raise ValueError(
            "chunk/vector ids differ; re-run the embed phase. "
            f"missing={missing[:3]} extra={extra[:3]}"
        )

    expected = config.embedding.expected_dim
    dims = {len(vector) for vector in embeddings["vectors"]}
    if dims != {expected}:
        raise ValueError(f"embeddings are not {expected}-dim: got {sorted(dims)}")

    client = _open_client(config)
    if reset:
        try:
            client.delete_collection(config.chroma.collection)
        except Exception:
            pass
    collection = client.get_or_create_collection(
        name=config.chroma.collection,
        metadata={
            "hnsw:space": config.chroma.space,
            "embedding_model": config.embedding.model,
            "dim": str(expected),
        },
    )

    vectors = embeddings["vectors"]
    batch_size = config.chroma.batch_size
    for start in range(0, len(chunks), batch_size):
        chunk_batch = chunks[start : start + batch_size]
        collection.upsert(
            ids=[chunk["chunk_id"] for chunk in chunk_batch],
            embeddings=vectors[start : start + batch_size],
            documents=[chunk["text"] for chunk in chunk_batch],
            metadatas=[_metadata(chunk) for chunk in chunk_batch],
        )

    count = collection.count()
    if count != len(chunks):
        raise RuntimeError(
            f"index count {count} != chunk count {len(chunks)}; "
            "the collection is inconsistent, re-run the index phase"
        )

    # Round-trip: retrieval needs text + url straight from Chroma.
    probe = collection.get(ids=[chunk_ids[0]], include=["documents", "metadatas"])
    stored = (probe.get("documents") or [""])[0]
    stored_meta = (probe.get("metadatas") or [{}])[0]
    if stored != chunks[0]["text"]:
        raise RuntimeError("stored document text does not match the source chunk")
    if stored_meta.get("source_url") != chunks[0]["source_url"]:
        raise RuntimeError("stored metadata lost the source_url")

    accept_store(config, chunks, embeddings, collection)
    manifest = {
        "phase": "06_vectordb",
        "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collection": config.chroma.collection,
        "persist_dir": str(
            config.chroma.persist_dir.relative_to(config.project_root)
        ),
        "embedding_model": config.embedding.model,
        "space": config.chroma.space,
        "dim": expected,
        "count": count,
        "chunks_written": len(chunks),
        "count_matches_chunks": True,
        "upsert_batch_size": batch_size,
        "reset": reset,
    }
    write_json(config.vectordb_dir / "manifest.json", manifest)
    print(
        f"Indexed {count} / {len(chunks)} chunks into "
        f"'{config.chroma.collection}' ({config.chroma.space})."
    )

    if verify:
        from src.ingest.verify import verify_index

        verify_index(config)

    return manifest


def main() -> None:
    index_chunks()


if __name__ == "__main__":
    main()
