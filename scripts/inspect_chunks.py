"""Small debug helper: print chunk headings/text for the build."""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "artifacts" / "02_chunks" / "chunks.jsonl"
chunks = [json.loads(line) for line in path.open(encoding="utf-8")]

for source_id in ("groww-large-cap", "groww-amc-hdfc"):
    print("===", source_id)
    for chunk in chunks:
        if chunk["source_id"] == source_id:
            text = chunk["text"][:150].replace("\n", " / ")
            print(f"[{chunk['kind']}] {chunk['heading']}: {text}")

print("\nHEADINGS:")
for heading, count in collections.Counter(c["heading"] for c in chunks).most_common(50):
    print(f"{count:>3}  {heading}")

returns = [c for c in chunks if "return" in c["text"].lower()]
print(f"\nChunks mentioning 'return': {len(returns)}")
for chunk in returns[:10]:
    print(" -", chunk["source_id"], "|", chunk["heading"])
