"""Shared configuration objects loaded from ``config.yaml`` + ``.env``."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ChromaConfig:
    persist_dir: Path
    collection: str
    space: str = "cosine"
    batch_size: int = 128


@dataclass(frozen=True)
class EmbeddingConfig:
    model: str
    batch_size: int = 32
    normalize: bool = True
    expected_dim: int = 384


@dataclass(frozen=True)
class ChunkingConfig:
    strategy: str
    max_chars: int
    overlap_chars: int
    min_chars: int = 40
    max_tokens: int = 256


@dataclass(frozen=True)
class RetrievalConfig:
    k: int
    min_score: float
    candidate_k: int = 24
    filter_by_scheme: bool = True


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    fallback_to_extractive: bool
    api_key: str
    model: str


@dataclass(frozen=True)
class GuardConfig:
    educational_url: str
    returns_url: str
    factsheet_url: str
    covered_scheme_ids: tuple[str, ...]


@dataclass(frozen=True)
class PolicyConfig:
    max_sentences: int
    last_updated_prefix: str
    refusal_last_updated: str


@dataclass(frozen=True)
class UiConfig:
    title: str
    welcome: str
    disclaimer: str
    example_questions: tuple[str, ...]
    show_artifacts: bool = True


@dataclass(frozen=True)
class Phase3CheckConfig:
    """Acceptance probe for the embed + index phase."""

    query: str
    expect_scheme: str
    expect_heading_contains: str
    top_k: int = 3


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    sources_file: Path
    artifacts_dir: Path
    chroma: ChromaConfig
    embedding: EmbeddingConfig
    chunking: ChunkingConfig
    retrieval: RetrievalConfig
    llm: LlmConfig
    guard: GuardConfig
    policy: PolicyConfig
    ui: UiConfig
    phase3_check: Phase3CheckConfig
    raw: dict = field(default_factory=dict, repr=False)

    # ---- artifact locations -------------------------------------------------
    @property
    def raw_dir(self) -> Path:
        return self.artifacts_dir / "01_raw"

    @property
    def loaded_dir(self) -> Path:
        return self.artifacts_dir / "01_loaded"

    @property
    def chunks_dir(self) -> Path:
        return self.artifacts_dir / "02_chunks"

    @property
    def embeddings_dir(self) -> Path:
        return self.artifacts_dir / "03_embeddings"

    @property
    def vectordb_dir(self) -> Path:
        return self.artifacts_dir / "04_vectordb"

    @property
    def retrieval_dir(self) -> Path:
        return self.artifacts_dir / "05_retrieval"

    @property
    def generation_dir(self) -> Path:
        return self.artifacts_dir / "06_generation"

    @property
    def eval_dir(self) -> Path:
        return self.artifacts_dir / "eval"

    def artifact_dirs(self) -> list[Path]:
        return [
            self.raw_dir,
            self.loaded_dir,
            self.chunks_dir,
            self.embeddings_dir,
            self.vectordb_dir,
            self.retrieval_dir,
            self.generation_dir,
            self.eval_dir,
            self.chroma.persist_dir,
        ]

    def ensure_dirs(self) -> None:
        for path in self.artifact_dirs():
            path.mkdir(parents=True, exist_ok=True)


_PROVIDER_ENV = {
    "groq": ("GROQ_API_KEY", "GROQ_MODEL", "qwen/qwen3.8-27b"),
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o-mini"),
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL", "gemini-2.5-flash"),
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
    "mistral": ("MISTRAL_API_KEY", "MISTRAL_MODEL", "mistral-small-latest"),
    "extractive": ("", "", "extractive"),
}


def _resolve_llm(raw: dict) -> LlmConfig:
    provider = str(raw.get("provider", "groq")).lower()
    key_env, model_env, default_model = _PROVIDER_ENV.get(
        provider, _PROVIDER_ENV["groq"]
    )
    api_key = os.environ.get(key_env, "") if key_env else ""
    model = (os.environ.get(model_env, "") if model_env else "") or default_model
    return LlmConfig(
        provider=provider,
        temperature=float(raw.get("temperature", 0.1)),
        max_tokens=int(raw.get("max_tokens", 256)),
        timeout_seconds=int(raw.get("timeout_seconds", 45)),
        fallback_to_extractive=bool(raw.get("fallback_to_extractive", True)),
        api_key=api_key.strip(),
        model=model.strip(),
    )


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load config.yaml and .env exactly once per call (cheap, no side effects)."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    path = Path(config_path) if config_path else PROJECT_ROOT / "config.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    artifacts_dir = PROJECT_ROOT / raw["artifacts_dir"]
    chunking = raw["chunking"]
    retrieval = raw["retrieval"]
    guard = raw.get("guard", {})
    policy = raw.get("policy", {})
    ui = raw["ui"]
    phase3 = raw.get("verify", {}).get("phase3", {})

    return AppConfig(
        project_root=PROJECT_ROOT,
        sources_file=PROJECT_ROOT / raw["sources_file"],
        artifacts_dir=artifacts_dir,
        chroma=ChromaConfig(
            persist_dir=PROJECT_ROOT / raw["chroma"]["persist_dir"],
            collection=raw["chroma"]["collection"],
            space=str(raw["chroma"].get("space", "cosine")),
            batch_size=int(raw["chroma"].get("batch_size", 128)),
        ),
        embedding=EmbeddingConfig(
            model=raw["embedding"]["model"],
            batch_size=int(raw["embedding"].get("batch_size", 32)),
            normalize=bool(raw["embedding"].get("normalize", True)),
            expected_dim=int(raw["embedding"].get("expected_dim", 384)),
        ),
        chunking=ChunkingConfig(
            strategy=chunking.get("strategy", "heading_then_recursive"),
            max_chars=int(chunking.get("max_chars", 900)),
            overlap_chars=int(chunking.get("overlap_chars", 120)),
            min_chars=int(chunking.get("min_chars", 40)),
            max_tokens=int(chunking.get("max_tokens", 256)),
        ),
        retrieval=RetrievalConfig(
            k=int(retrieval.get("k", 5)),
            min_score=float(retrieval.get("min_score", 0.30)),
            candidate_k=int(retrieval.get("candidate_k", 24)),
            filter_by_scheme=bool(retrieval.get("filter_by_scheme", True)),
        ),
        llm=_resolve_llm(raw.get("llm", {})),
        guard=GuardConfig(
            educational_url=guard.get(
                "educational_url", "https://investor.sebi.gov.in/"
            ),
            returns_url=guard.get(
                "returns_url", "https://investor.sebi.gov.in/personalinvestments.html"
            ),
            factsheet_url=guard.get(
                "factsheet_url", "https://www.hdfcfund.com/mutual-funds/factsheets"
            ),
            covered_scheme_ids=tuple(guard.get("covered_scheme_ids", [])),
        ),
        policy=PolicyConfig(
            max_sentences=int(policy.get("max_sentences", 3)),
            last_updated_prefix=str(
                policy.get("last_updated_prefix", "Last updated from sources: ")
            ),
            refusal_last_updated=str(
                policy.get(
                    "refusal_last_updated",
                    "Last updated from sources: policy response (no scheme data used)",
                )
            ),
        ),
        ui=UiConfig(
            title=ui.get("title", "Groww Mutual Fund FAQ Assistant"),
            welcome=ui.get(
                "welcome",
                "Ask factual questions about selected HDFC Mutual Fund schemes.",
            ),
            disclaimer=ui.get("disclaimer", "Facts-only. No investment advice."),
            example_questions=tuple(ui.get("example_questions", [])),
            show_artifacts=bool(ui.get("show_artifacts", True)),
        ),
        phase3_check=Phase3CheckConfig(
            query=str(phase3.get("query", "expense ratio ELSS")),
            expect_scheme=str(phase3.get("expect_scheme", "")),
            expect_heading_contains=str(
                phase3.get("expect_heading_contains", "")
            ).lower(),
            top_k=int(phase3.get("top_k", 3)),
        ),
        raw=raw,
    )
