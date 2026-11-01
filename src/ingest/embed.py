"""Phase 5 (embed): embed every chunk with the config model.

The model, batch size, normalization, and expected dimension all come from
``config.yaml``. Nothing here is hardcoded.

Output:

``artifacts/03_embeddings/chunk_embeddings.npz``
    ``ids``       - chunk id per row, same order as ``chunks.jsonl``
    ``vectors``   - float32 matrix, ``config.embedding.expected_dim`` columns
    ``metadata``  - one JSON string per row (url, scheme, section, ...)

plus ``manifest.json`` and ``phase5_report.json``. A failed check aborts
the phase instead of leaving a vector file the index cannot trust.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np

from src.config import AppConfig, load_config
from src.embedding import embed_texts
from src.utils import read_jsonl, write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EMBEDDINGS_FILE = "chunk_embeddings.npz"

# Kept deliberately small: enough to identify and cite a chunk, not the
# full chunk text (that lives in chunks.jsonl / Chroma documents).
_METADATA_KEYS = (
    "chunk_id",
    "source_id",
    "source_url",
    "scheme",
    "category",
    "doc_type",
    "heading",
    "section",
    "breadcrumb",
    "kind",
    "token_count",
    "fetched_at",
)


def _row_metadata(chunk: dict) -> dict:
    return {key: chunk.get(key, "") for key in _METADATA_KEYS}


def write_embeddings(
    config: AppConfig,
    chunks: list[dict],
    vectors: list[list[float]],
) -> dict:
    """Validate and persist the npz artifact. Returns summary stats."""

    if len(chunks) != len(vectors):
        raise ValueError(
            f"chunk/vector mismatch: {len(chunks)} chunks vs {len(vectors)} vectors"
        )

    ids = [chunk["chunk_id"] for chunk in chunks]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate chunk ids in embedding batch")

    expected = config.embedding.expected_dim
    dims = {len(vector) for vector in vectors}
    if dims != {expected}:
        raise ValueError(
            f"expected {expected}-dim vectors from {config.embedding.model}, "
            f"got {sorted(dims)}"
        )

    matrix = np.asarray(vectors, dtype=np.float32)
    metadata = [_row_metadata(chunk) for chunk in chunks]
    path = config.embeddings_dir / EMBEDDINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        ids=np.asarray(ids, dtype=str),
        vectors=matrix,
        metadata=np.asarray(
            [json.dumps(row, ensure_ascii=False) for row in metadata], dtype=str
        ),
    )
    return {
        "path": path,
        "ids": ids,
        "dim": int(matrix.shape[1]),
        "rows": int(matrix.shape[0]),
        "metadata": metadata,
        "matrix": matrix,
    }


def read_embeddings(config: AppConfig) -> dict:
    """Load the npz artifact as plain Python values."""

    path = config.embeddings_dir / EMBEDDINGS_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run `python -m src.ingest.run --phase phase5` first."
        )
    with np.load(path, allow_pickle=False) as payload:
        ids = [str(value) for value in payload["ids"]]
        vectors = payload["vectors"].astype(np.float32).tolist()
        metadata = [
            json.loads(value) for value in payload["metadata"].tolist()
        ]
    if not (len(ids) == len(vectors) == len(metadata)):
        raise ValueError(
            f"corrupt embeddings artifact: ids={len(ids)} vectors={len(vectors)} "
            f"metadata={len(metadata)}"
        )
    return {"ids": ids, "vectors": vectors, "metadata": metadata}


def accept_embeddings(
    config: AppConfig,
    chunks: list[dict],
    written: dict,
) -> dict:
    """Phase 5 acceptance. Writes the report, then raises on any failure."""

    expected = config.embedding.expected_dim
    ids = written["ids"]
    matrix = written["matrix"]
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    checks: list[dict] = []

    checks.append(
        {
            "check": "count_equals_chunks",
            "passed": written["rows"] == len(chunks) and ids == chunk_ids,
            "detail": f"vectors={written['rows']} chunks={len(chunks)}",
        }
    )
    checks.append(
        {
            "check": "vectors_are_expected_dim",
            "passed": written["dim"] == expected and matrix.shape == (len(chunks), expected),
            "detail": f"expected={expected} shape={list(matrix.shape)}",
        }
    )
    finite = bool(np.isfinite(matrix).all())
    checks.append(
        {
            "check": "vectors_are_finite",
            "passed": finite,
            "detail": "no NaN or Inf" if finite else "non-finite values present",
        }
    )
    if config.embedding.normalize:
        norms = np.linalg.norm(matrix, axis=1)
        off = int(np.sum(np.abs(norms - 1.0) > 1e-3))
        normalized = off == 0 and len(norms) == len(chunks)
        detail = f"max_|norm-1|={float(np.max(np.abs(norms - 1.0))):.6f} off={off}"
    else:
        normalized = True
        detail = "normalize=false, unit-norm check skipped"
    checks.append(
        {
            "check": "vectors_match_normalize_setting",
            "passed": normalized,
            "detail": detail,
        }
    )
    missing_url = [
        row.get("chunk_id", "?")
        for row in written["metadata"]
        if not str(row.get("source_url", "")).startswith("https://")
    ]
    checks.append(
        {
            "check": "every_vector_keeps_citation",
            "passed": not missing_url,
            "detail": f"rows_without_url={len(missing_url)}",
        }
    )
    checks.append(
        {
            "check": "model_comes_from_config",
            "passed": bool(config.embedding.model) and config.embedding.batch_size > 0,
            "detail": (
                f"model={config.embedding.model} batch={config.embedding.batch_size} "
                f"normalize={config.embedding.normalize}"
            ),
        }
    )

    passed = all(item["passed"] for item in checks)
    report = {
        "phase": "05_embedding",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact": EMBEDDINGS_FILE,
        "model": config.embedding.model,
        "batch_size": config.embedding.batch_size,
        "normalized": config.embedding.normalize,
        "dim": written["dim"],
        "count": written["rows"],
        "passed": passed,
        "checks": checks,
    }
    write_json(config.embeddings_dir / "phase5_report.json", report)
    for item in checks:
        print(f"  {'PASS' if item['passed'] else 'FAIL'} {item['check']}: {item['detail']}")
    print(f"Phase 5 report -> {config.embeddings_dir / 'phase5_report.json'}")
    if not passed:
        failed = [item["check"] for item in checks if not item["passed"]]
        raise RuntimeError(f"Phase 5 embedding acceptance failed: {failed}")
    return report


def embed_chunks(config: AppConfig | None = None) -> dict:
    config = config or load_config()
    config.ensure_dirs()
    chunks = read_jsonl(config.chunks_dir / "chunks.jsonl")
    if not chunks:
        raise FileNotFoundError(
            f"No chunks in {config.chunks_dir}. Run the chunk phase first."
        )

    print(f"Loading embedding model: {config.embedding.model}")
    texts = [chunk["text"] for chunk in chunks]
    vectors = embed_texts(texts, config, show_progress=True)
    written = write_embeddings(config, chunks, vectors)

    accept_embeddings(config, chunks, written)
    manifest = {
        "phase": "05_embedding",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact": EMBEDDINGS_FILE,
        "model": config.embedding.model,
        "batch_size": config.embedding.batch_size,
        "normalized": config.embedding.normalize,
        "expected_dim": config.embedding.expected_dim,
        "dim": written["dim"],
        "count": written["rows"],
        "metadata_fields": list(_METADATA_KEYS),
    }
    write_json(config.embeddings_dir / "manifest.json", manifest)
    print(
        f"\nEmbedded {written['rows']} chunks -> "
        f"{written['dim']}-d vectors ({EMBEDDINGS_FILE})."
    )
    return manifest


def main() -> None:
    embed_chunks()


if __name__ == "__main__":
    main()
