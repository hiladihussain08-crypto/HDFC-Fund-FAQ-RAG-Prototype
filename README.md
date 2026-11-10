---
title: HDFC Fund FAQ
emoji: "📄"
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
---

# Groww Mutual Fund FAQ Assistant

A small, facts-only RAG prototype that answers factual questions about four HDFC
Mutual Fund schemes using official Groww, SEBI, AMFI, and CAMS pages. Every answer
is at most three sentences, carries **exactly one citation URL**, and ends with
`Last updated from sources: <date>`.

> **Facts-only. No investment advice.**
> This assistant shares publicly available scheme facts (e.g., expense ratio, exit load,
> minimum SIP, lock-in, riskometer, benchmark) with one source link per answer.
> It does not recommend, advise, or predict — please read all scheme-related documents
> carefully before investing. Mutual fund investments are subject to market risks.

## Covered schemes

| Scheme | Groww page |
|---|---|
| HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| HDFC Flexi Cap Direct Plan Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| HDFC ELSS Tax Saver Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| HDFC Mid Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |

Questions about other AMCs, uncovered HDFC schemes, returns/NAV/performance,
investment advice, or PII are refused or reported as outside the loaded corpus.
The full 19-URL source list is in [`deliverables/sources.md`](deliverables/sources.md).

## What works

- Guardrail routing before retrieval: factual / advice-refusal / returns-refusal /
  PII-refusal / not-in-corpus.
- Scheme detection before retrieval, so a question about SBI Bluechip or HDFC Small
  Cap cannot be answered with a similar but different HDFC scheme.
- Structured fact chunks (expense ratio, exit load, minimum SIP/lump-sum, lock-in,
  riskometer, benchmark, fund manager, fund house, AUM, launch date, stamp duty,
  category) with an authored one-sentence answer per fact.
- Section chunks for statement how-tos and investor education.
- Exactly one citation per response, selected from retrieved official pages.
- `Last updated from sources: 2026-11-01` on every response.
- PII is detected before persistence; the stored question is
  `[redacted: PII detected]`.
- Deterministic extractive fallback when no LLM key is configured, so the demo
  runs without a paid API key.

Evaluation: **28/28 behaviour cases pass**, plus structural checks for all RAG
stages (`python scripts/eval_guardrails.py`).

## RAG stages and inspectable artifacts

Each stage persists its own output under `artifacts/`. The Streamlit UI can browse
every file, and the query pipeline writes one JSON per question for the retrieval
and generation stages.

| Stage | Command | Artifact |
|---|---|---|
| 0. Directories | `python -m src.ingest.run --phase dirs` | `artifacts/` |
| 1. Load/scrape | `python -m src.ingest.run --phase scrape` | `artifacts/01_raw/<id>.html` + `<id>.json` |
| 2. Clean documents | `python -m src.ingest.run --phase load` | `artifacts/01_loaded/documents.jsonl` + manifest |
| Chunk (phase 4) | `python -m src.ingest.run --phase phase4` | `artifacts/02_chunks/chunks.jsonl`, `chunks_summary.csv`, `phase4_report.json` |
| Embed (phase 5) | `python -m src.ingest.run --phase phase5` | `artifacts/03_embeddings/chunk_embeddings.npz`, `phase5_report.json` |
| Vector DB (phase 6) | `python -m src.ingest.run --phase phase6` | `chroma_db/` + `artifacts/04_vectordb/phase6_report.json` |
| Embed + index (PRD phase 3) | `python -m src.ingest.run --phase phase3` | above + `artifacts/04_vectordb/phase3_report.json` |
| 7. Retrieve (phase 7) | `python -m src.ingest.run --phase phase7` | `artifacts/05_retrieval/phase7_report.json` |
| 6. Retrieve (per question) | `python -m src.query.pipeline "..."` | `artifacts/05_retrieval/<query_id>.json` |
| 7. Generate | same command | `artifacts/06_generation/<query_id>.json` |
| Eval | `python scripts/eval_guardrails.py` | `artifacts/eval/eval_report.json` |

Run all ingest phases in one command:

```powershell
python -m src.ingest.run --phase all
# Reuse cached HTML without re-scraping:
python -m src.ingest.run --phase all --reuse-raw
```

Ask a question:

```powershell
python -m src.query.pipeline "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"
python -m src.query.pipeline "Should I buy HDFC Large Cap now?"
python -m src.query.pipeline "How do I download my capital gains statement?" --json
```

Start the UI:

```powershell
streamlit run src/ui/app.py
```

## Setup

Tested with Python 3.12 on Windows. The project venv is `.venv`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The first embed run downloads `sentence-transformers/all-MiniLM-L6-v2` from
Hugging Face (~90 MB). The model is cached for later runs.

### LLM configuration

`config.yaml` selects the provider (`groq` by default). Secrets and model ids live
in `.env`, which is git-ignored:

```dotenv
GROQ_API_KEY=your_key_here
GROQ_MODEL=qwen/qwen3.8-27b
```

With no `GROQ_API_KEY`, the pipeline logs `missing_api_key` in the generation
artifact and uses the deterministic extractive answer. Set the key and re-run the
same command to use Groq; no code changes are needed. Other providers
(`openai`, `gemini`, `anthropic`, `mistral`, or `extractive`) can be selected in
`config.yaml` and their keys placed in `.env`.

Configuration knobs include the embedding model, chunk sizes/overlap, Chroma
collection and path, retrieval `k`/`min_score`, LLM provider/temperature/model, UI
example questions, and refusal links. Nothing about the model, DB, or keys is
hardcoded in the pipeline.

## Guardrails

The order is: PII → advice/opinion → returns/performance → foreign/uncovered
scheme → missing scheme → factual retrieval.

- **PII:** PAN, Aadhaar, phone, email, OTP, account number, IFSC, UPI ID, and card
  patterns are refused before logging. Artifacts store only the redaction marker.
- **Advice:** buy/sell/hold, ranking, portfolio, "best", "should I", and timing
  questions get a polite refusal plus a SEBI Investor Education link.
- **Returns:** return, CAGR, NAV, performance, comparison, and "last year"
  questions get a returns refusal plus a SEBI education link. No return values are
  embedded in the corpus; return/holdings/peer tables are filtered out at chunking.
- **Out of corpus:** other AMCs and uncovered HDFC schemes get an honest miss plus
  the AMC overview link.
- **Citation:** the LLM never chooses the URL. The application attaches the URL of
  the retrieved chunk that supplied the answer.

## Design decisions

1. **Groww `__NEXT_DATA__` first.** Scheme and AMC pages expose server-rendered
   structured facts. The loader reads those exact values instead of regexing the
   rendered page, which avoids NAV/return contamination and transcription errors.
2. **Atomic fact chunks.** Each scheme fact becomes one self-contained chunk with
   an authored answer. This keeps labels and values together for MiniLM and makes
   citations precise.
3. **Filter before embedding.** AMC marketing copy, "how to invest" walkthroughs,
   return tables, holdings, peer comparisons, and generic footers are dropped.
4. **Conservative corpus.** `hdfcfund.com` returns HTTP 403 to automated clients,
   and the CAMS page is JavaScript-rendered. Those URLs remain official reference
   targets but are not embedded. See `deliverables/sources.md`.

## Project layout

```
hdfc-mf-faq/
  config.yaml               # all tunable, non-secret settings
  .env.example              # provider keys/model ids template
  data/sources.csv          # 19 official URLs + what each evidences
  src/
    config.py               # YAML + .env -> frozen dataclasses
    schemes.py              # scheme aliases, foreign/uncovered detection
    embedding.py            # shared MiniLM embedder for ingest + query
    ingest/                 # scrape, load, chunk, embed, index, CLI
    query/                  # guard, retrieve, llm, generate, pipeline
    ui/app.py               # tiny Streamlit UI + artifact browser
  scripts/
    eval_guardrails.py      # 28-case golden/refusal/PII/structural eval
    build_docs.py           # regenerate sources.md + sample_qa.md
  deliverables/
    sources.md              # 19-URL official source list
    sample_qa.md            # 10 real Q&A transcripts
    disclaimer.md           # copy-paste disclaimer
  artifacts/                # per-stage, human-readable RAG evidence
  chroma_db/                # persistent Chroma collection
```

## Deliverables

- Working prototype: this repository + `python -m src.ingest.run --phase all`,
  then `streamlit run src/ui/app.py`.
- Source list: [`deliverables/sources.md`](deliverables/sources.md) (19 URLs).
- Sample Q&A: [`deliverables/sample_qa.md`](deliverables/sample_qa.md) (10 queries).
- Disclaimer: [`deliverables/disclaimer.md`](deliverables/disclaimer.md), also shown
  in the UI and at the top of this README.
- RAG artifacts: `artifacts/01_raw` → `artifacts/06_generation`, browsable in the
  UI's "RAG stage artifacts" section.

## Known limits

- The corpus is intentionally small: four schemes plus AMC/education/help pages.
  Other schemes and AMCs are refused rather than approximated.
- Scheme facts are from Groww pages fetched on 2026-11-01. Re-run the ingest
  pipeline to refresh them.
- `hdfcfund.com` blocks automated fetching (HTTP 403), and the CAMS page is
  JavaScript-only, so neither contributes embedded chunks.
- MiniLM can miss unusual synonyms; the atomic fact chunks and scheme filter
  mitigate this but do not guarantee every paraphrase.
- The app is single-turn by design: no chat memory and no PII storage.
- The default demo path is the extractive fallback because no Groq key is
  committed. With a key, the same retrieved context is sent to
  `qwen/qwen3.8-27b` through Groq.

## Tests

```powershell
python scripts/eval_guardrails.py
python scripts/build_docs.py   # refresh sources.md and sample_qa.md
```

`eval_guardrails.py` checks route, answer facts, ≤3 sentences, exactly one
allowlisted citation, the last-updated stamp, PII non-persistence, artifact
completeness, 384-dimensional embeddings, chunk/Chroma count parity, and the
absence of returns tables in the corpus. The phase-3 runner additionally
writes `phase3_report.json`: collection count equals chunk count, every
embedded chunk is indexed, vectors are the configured dimension, the
collection uses the configured distance space, every row keeps its citation
URL, and a sanity query ("expense ratio ELSS") lands the ELSS expense-ratio
fact chunk in the top 3.
