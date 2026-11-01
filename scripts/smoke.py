"""Quick end-to-end smoke run for the FAQ pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.query.pipeline import answer_question  # noqa: E402

QUESTIONS = [
    "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    "What is the expense ratio of HDFC ELSS Tax Saver Fund Direct Plan Growth?",
    "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
    "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
    "What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?",
    "What is the exit load of HDFC Flexi Cap Direct Plan Growth?",
    "What is the benchmark of HDFC Mid Cap Fund Direct Growth?",
    "What is the riskometer level of HDFC ELSS Tax Saver Fund?",
    "Who manages HDFC Large Cap Fund Direct Growth?",
    "How do I download my capital gains statement?",
    "What is the exit load if I redeem within 1 year?",
    "Should I buy HDFC Large Cap now?",
    "Which is better, Mid Cap or Flexi Cap?",
    "How did the fund perform last year?",
    "My PAN is ABCDE1234F, what is my expense ratio?",
    "What is the expense ratio of SBI Bluechip Fund?",
    "What is the expense ratio of HDFC Small Cap Fund?",
    "Tell me a joke",
]

for question in QUESTIONS:
    response = answer_question(question, persist=True)
    print("=" * 100)
    print("Q:", question)
    print("route:", response["route"], "| reason:", response["reason"], "| mode:",
          response["generation"].get("mode", "policy"), "| intent:", response["intent"])
    print("A:", response["answer"])
    print("source:", response["citation_url"])
    print(response["last_updated"])
    top = response["hits"][:1]
    for hit in top:
        print(f"top: {hit['score']:.3f} {hit['source_id']} :: {hit['heading']}")
