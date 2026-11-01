"""Print loaded document headings by source to spot extraction noise."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
docs = [
    json.loads(line)
    for line in (ROOT / "artifacts" / "01_loaded" / "documents.jsonl").open(encoding="utf-8")
]
for doc in docs:
    print(f"\n=== {doc['id']} [{doc['doc_type']}] {doc['char_count']} chars")
    for section in doc["sections"]:
        print(f"  - {section['heading']}: {section['text'][:100].replace(chr(10), ' / ')}")
