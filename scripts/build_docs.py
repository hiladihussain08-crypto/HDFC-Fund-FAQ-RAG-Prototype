"""Regenerate the deliverable markdown from the live corpus and pipeline.

Outputs:
  deliverables/sources.md     - 19-URL official source list with fetch status
  deliverables/sample_qa.md   - 10 real Q&A transcripts
  deliverables/disclaimer.md  - copy-paste disclaimer snippet
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.config import load_config  # noqa: E402
from src.query.pipeline import answer_question  # noqa: E402
from src.utils import read_json  # noqa: E402

SAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
    "What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?",
    "What is the exit load of HDFC Flexi Cap Direct Plan Growth?",
    "What is the benchmark of HDFC Mid Cap Fund Direct Growth?",
    "What is the riskometer level of HDFC ELSS Tax Saver Fund?",
    "How do I download my capital gains statement?",
    "Should I buy HDFC Large Cap now?",
    "How did the fund perform last year?",
    "What is the expense ratio of SBI Bluechip Fund?",
]

DISCLAIMER = """**Facts-only. No investment advice.**

This assistant shares publicly available scheme facts (e.g., expense ratio, exit load,
minimum SIP, lock-in, riskometer, benchmark) with one source link per answer.
It does not recommend, advise, or predict — please read all scheme-related documents
carefully before investing. Mutual fund investments are subject to market risks.
"""


def build_sources(config) -> Path:
    rows = list(
        csv.DictReader(config.sources_file.open(encoding="utf-8-sig", newline=""))
    )
    lines = [
        "# Official source list",
        "",
        f"{len(rows)} official public URLs used by the prototype. The first five Groww",
        "pages carry the scheme/AMC facts; the rest support statement how-tos and",
        "investor-education refusals. No third-party blogs or app back-end endpoints.",
        "",
        "| # | Category | Page | URL | What it evidences | Fetch status |",
        "|---|---|---|---|---|---|",
    ]
    for index, row in enumerate(rows, start=1):
        meta = {}
        meta_path = config.raw_dir / f"{row['id']}.json"
        if meta_path.exists():
            meta = read_json(meta_path)
        status = meta.get("http_status", "not fetched")
        fetched = (meta.get("fetched_at") or "")[:10]
        status_text = f"{status}"
        if fetched:
            status_text += f" on {fetched}"
        if row["id"] == "cams-cas":
            status_text += " (link-only)"
        lines.append(
            f"| {index} | {row['category']} | {row['title']} | "
            f"[{row['url']}]({row['url']}) | {row.get('evidences', '')} | "
            f"{status_text} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- `groww-amc-hdfc` and the four scheme pages expose structured facts in",
        "  `__NEXT_DATA__`; the loader reads those exact values instead of guessing",
        "  from rendered text.",
        "- `cams-cas` is retained as an official reference/citation target. Its body",
        "  is rendered by JavaScript and yields no extractable text, so it is not",
        "  embedded in the vector store.",
        "- `hdfcfund.com` was checked but returns HTTP 403 to automated clients, so",
        "  official HDFC AMC pages are not part of the crawled corpus.",
        "",
    ]
    path = ROOT / "deliverables" / "sources.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_sample_qa(config) -> Path:
    lines = [
        "# Sample Q&A",
        "",
        "These are real transcripts from `src.query.pipeline.answer_question` against",
        "the committed corpus (2026-11-01). Each answer is at most three sentences,",
        "carries exactly one citation, and ends with the source date.",
        "",
        "> **Facts-only. No investment advice.**",
        "",
    ]
    for index, question in enumerate(SAMPLE_QUESTIONS, start=1):
        response = answer_question(question, config, persist=False)
        lines += [
            f"## {index}. {question}",
            "",
            f"**Answer:** {response['answer']}",
            "",
            f"**Citation:** {response['citation_url']}",
            "",
            f"**{response['last_updated']}**",
            "",
            f"*Type:* `{response['route']}` · *mode:* "
            f"`{response['generation'].get('mode', 'policy_response')}`",
            "",
        ]
    path = ROOT / "deliverables" / "sample_qa.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_disclaimer() -> Path:
    path = ROOT / "deliverables" / "disclaimer.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DISCLAIMER, encoding="utf-8")
    return path


def main() -> None:
    config = load_config()
    for path in (build_sources(config), build_sample_qa(config), build_disclaimer()):
        print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
