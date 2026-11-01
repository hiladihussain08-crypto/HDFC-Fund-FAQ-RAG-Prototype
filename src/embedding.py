"""One shared embedding model for ingest and query (config-driven)."""

from __future__ import annotations

import os
from functools import lru_cache

from src.config import AppConfig

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

_MODEL_CACHE: dict[str, object] = {}


def get_model(config: AppConfig):
    """Load ``config.embedding.model`` once per process."""

    name = config.embedding.model
    if name not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer

        _MODEL_CACHE[name] = SentenceTransformer(name)
    return _MODEL_CACHE[name]


@lru_cache(maxsize=1024)
def embed_query_cached(text: str, model_name: str) -> tuple[float, ...]:
    # Kept for callers that need a cheap, immutable cache key.
    raise RuntimeError("Use embed_query() so the config model is honoured.")


def embed_texts(
    texts: list[str],
    config: AppConfig,
    show_progress: bool = False,
) -> list[list[float]]:
    if not texts:
        return []
    model = get_model(config)
    vectors = model.encode(
        texts,
        batch_size=config.embedding.batch_size,
        normalize_embeddings=config.embedding.normalize,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
    )
    return [[float(value) for value in row] for row in vectors]


def embed_query(text: str, config: AppConfig) -> list[float]:
    return embed_texts([text], config, show_progress=False)[0]
