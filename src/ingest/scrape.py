"""Phase 1 (scrape): fetch every public source into ``artifacts/01_raw``.

Writes ``{id}.html``, ``{id}.json`` (URL metadata) and ``manifest.json``.
A failed page is recorded, never silently dropped.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import AppConfig, load_config
from src.ingest.http import fetch
from src.utils import write_json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_sources(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"id", "category", "title", "url"}
    if rows and not required.issubset(rows[0].keys()):
        missing = required - set(rows[0].keys())
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    return rows


def scrape_all(config: AppConfig | None = None) -> list[dict[str, Any]]:
    config = config or load_config()
    config.ensure_dirs()
    raw_dir = config.raw_dir
    sources = load_sources(config.sources_file)

    records: list[dict[str, Any]] = []
    for row in sources:
        page_id = row["id"]
        url = row["url"]
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = fetch(url)

        html_path = raw_dir / f"{page_id}.html"
        html_path.write_bytes(result.body)

        record = {
            "id": page_id,
            "url": url,
            "final_url": result.final_url,
            "category": row.get("category", ""),
            "title": row.get("title", ""),
            "scheme": row.get("scheme", ""),
            "doc_type": row.get("doc_type", ""),
            "fetched_at": fetched_at,
            "http_status": result.status,
            "tls_verified": result.tls_verified,
            "error": result.error,
            "raw_html_path": str(
                Path("artifacts") / "01_raw" / f"{page_id}.html"
            ),
            "content_bytes": len(result.body),
        }
        write_json(raw_dir / f"{page_id}.json", record)
        records.append(record)
        flag = "ok  " if result.status == 200 else "fail"
        print(f"{flag} {result.status:>3} {page_id:<32} {len(result.body):>8} B")

    ok = sum(1 for item in records if item["http_status"] == 200)
    manifest = {
        "phase": "01_raw",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources_file": str(config.sources_file.relative_to(config.project_root)),
        "count": len(records),
        "ok": ok,
        "failed": len(records) - ok,
        "ids": [item["id"] for item in records],
        "failed_ids": [
            item["id"] for item in records if item["http_status"] != 200
        ],
    }
    write_json(raw_dir / "manifest.json", manifest)
    print(f"\nScraped {len(records)} pages ({ok} ok, {len(records) - ok} failed).")
    return records


def main() -> None:
    scrape_all()


if __name__ == "__main__":
    main()
