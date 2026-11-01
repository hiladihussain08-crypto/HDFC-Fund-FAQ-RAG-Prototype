"""Ingest CLI: directories -> scrape -> load -> chunk -> embed -> Chroma."""

from __future__ import annotations

import argparse
import sys

from src.config import load_config
from src.ingest.chunk import chunk_documents
from src.ingest.embed import embed_chunks
from src.ingest.index import index_chunks
from src.ingest.init_dirs import create_directories
from src.ingest.load import load_documents
from src.ingest.scrape import scrape_all
from src.query.retrieve import run_golden_set

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _banner(text: str) -> None:
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description="HDFC MF FAQ ingest pipeline")
    parser.add_argument(
        "--phase",
        default="all",
        help="all | dirs | scrape | load | chunk | phase4 | embed | phase5 | index | phase6 | phase7 | phase8 | phase3",
    )
    parser.add_argument(
        "--reuse-raw",
        action="store_true",
        help="With --phase all, skip scraping and reuse artifacts/01_raw.",
    )
    args = parser.parse_args()
    phase = str(args.phase).lower()
    config = load_config()

    if phase in {"dirs", "0"}:
        _banner("Phase 0 - directories")
        for path in create_directories():
            print(f"ok  {path}")
        return

    if phase in {"scrape", "1"}:
        _banner("Phase 1 - scrape public pages")
        scrape_all(config)
        return

    if phase in {"load", "2"}:
        _banner("Phase 2 - load documents")
        load_documents(config)
        return

    if phase in {"chunk", "3", "phase4", "chunking"}:
        _banner("Phase 4 - chunking")
        chunk_documents(config)
        return

    if phase in {"embed", "4", "phase5", "embedding"}:
        _banner("Phase 5 - embedding")
        embed_chunks(config)
        return

    if phase in {"index", "5", "phase6", "store", "vectordb"}:
        _banner("Phase 6 - storing in the vector DB")
        index_chunks(config)
        return

    if phase in {"phase7", "retrieve", "retrieval"}:
        _banner("Phase 7 - retrieval")
        run_golden_set(config)
        return

    if phase in {"phase8", "ui"}:
        _banner("Phase 8 - UI")
        print("Streamlit UI is available at src/ui/app.py")
        print("Start with: streamlit run src/ui/app.py")
        return

    if phase in {"phase3", "embed-index"}:
        _banner("Phase 3 - embed chunks + index in ChromaDB")
        embed_chunks(config)
        index_chunks(config)
        return

    if phase in {"all", "pipeline"}:
        _banner("Phase 0 - directories")
        create_directories()
        if not args.reuse_raw:
            _banner("Phase 1 - scrape public pages")
            scrape_all(config)
        _banner("Phase 2 - load documents")
        load_documents(config)
        _banner("Phase 4 - chunking")
        chunk_documents(config)
        _banner("Phase 5 - embedding")
        embed_chunks(config)
        _banner("Phase 6 - storing in the vector DB")
        index_chunks(config)
        _banner("Phase 7 - retrieval")
        run_golden_set(config)
        _banner("Done")
        print(f"Artifacts: {config.artifacts_dir}")
        print(f"Chroma:    {config.chroma.persist_dir}")
        return

    raise SystemExit(f"Unknown phase: {args.phase}")


if __name__ == "__main__":
    main()
