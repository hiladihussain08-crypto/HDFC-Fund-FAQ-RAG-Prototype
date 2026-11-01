"""Phase 0: create the directory layout (stdlib only)."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DIRECTORY_LAYOUT = [
    "data",
    "samples",
    "scripts",
    "src/ingest",
    "src/query",
    "src/ui",
    "artifacts/01_raw",
    "artifacts/01_loaded",
    "artifacts/02_chunks",
    "artifacts/03_embeddings",
    "artifacts/04_vectordb",
    "artifacts/05_retrieval",
    "artifacts/06_generation",
    "artifacts/eval",
    "chroma_db",
]


def directory_paths(root: Path | None = None) -> list[Path]:
    root = root or PROJECT_ROOT
    return [root / rel for rel in DIRECTORY_LAYOUT]


def create_directories(root: Path | None = None) -> list[Path]:
    created: list[Path] = []
    for path in directory_paths(root):
        path.mkdir(parents=True, exist_ok=True)
        gitkeep = path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
        created.append(path)
    return created


def main() -> None:
    for path in create_directories():
        print(f"ok  {path}")


if __name__ == "__main__":
    main()
