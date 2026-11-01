# Architecture — Mutual Fund FAQ Assistant (Facts-Only RAG)

> **Derived from:** [`PRD.md`](./PRD.md) v1.0 (which itself derives from
> [`ProblemStatement.txt`](./ProblemStatement.txt)).
> PRD gives the *what*; this document gives the *how* — components, data contracts,
> flows, and resilience behaviour for implementation.

| | |
|---|---|
| **System** | mf-faq-assistant-rag — small-corpus RAG demo (Load → Chunk → Embed → Index → Retrieve → Generate → Tiny UI) |
| **Corpus** | 5 official Groww pages (HDFC AMC overview + Large Cap / Flexi Cap / ELSS / Mid Cap) + curated official supporting pages |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (384-dim), shared by ingestion **and** retrieval |
| **Vector store** | ChromaDB persistent client (local filesystem), cosine distance |
| **LLM** | Provider abstraction; primary = Groq (OpenAI-compatible), model id from `.env` |
| **UI** | Streamlit single page (decision A-1) |
| **Runtime** | Single machine, local artifacts only; no server-side DB, no PII store |

---

## 1. Context view (system at a glance)

```
            User (retail user / support staff)
                        │  ask a question
                        ▼
        ┌───────────────────────────────────────┐
        │            Tiny UI (Streamlit)        │  welcome line · 3 example chips ·
        │                                       │  "Facts-only. No investment advice."
        └──────┬───────────────────▲────────────┘
               │ question          │ AnswerCard
               ▼                   │  (answer + 1 citation + Last updated + evidence expander)
 Part B — Q&A runtime pipeline
   [PII gate] → [Classifier] → [Retriever] → [LLM client] → [Answer post-checks]
                     │              │                │
               refusal paths   ChromaDB query    Groq (or other provider)
                     └──── same config-driven embedder + vector store ────┘
               offline artifacts: data/retrieval/*.json, retrieval log

 Part A — Ingestion pipeline (batch, re-runnable, phase-per-script)
   [1 Load] → data/raw/*.json → [2 Chunk] → data/chunks/chunks.jsonl
        → [3 Embed] → data/embeddings/*.npz → [3 Index] → data/chroma/ (persistent)
        → [Startup consistency checks]

 Shared configuration surface (single source of truth)
   config.yaml (phases, chunking, embedding, vector DB, retrieval top-k, LLM settings)
   .env        (LLM_PROVIDER, API keys, GROQ_MODEL)
```

Two **disjoint pipelines share exactly one config surface**; the retrieval path reuses the
identical embedding model and vector store keys that ingestion used (PRD §9.4) — enforced
at startup, not by convention (§10).

## 2. Component map

| # | Component | Code (module → file) | Responsibility | PRD ref |
|---|---|---|---|---|
| C1 | Configuration | `src/core/config.py` | Load `config.yaml` + `.env`; typed access; validation; freeze values | §10 |
| C2 | Loader (Phase 1) | `src/core/loader.py` | Fetch `scraping.pages`; robots/UA/timeout honored; write raw JSON per page | §9.1 |
| C3 | Chunker (Phase 2) | `src/core/chunker.py` | Section-split cleaned text w/ breadcrumbs; table → fact strips; metadata on every chunk; write `chunks.jsonl` + summary CSV | §9.2 |
| C4 | Embedder | `src/core/embedder.py` | Batch-encode chunks (384-dim, normalized); write `.npz` inspection artifact | §9.3 |
| C5 | Vector store | `src/core/vector_store.py` | ChromaDB persistent client; upsert text+metadata+vectors; cosine; query API | §9.3–9.4 |
| C6 | Retriever (Phase 4) | `src/core/retriever.py` | Embed query with **C4's model**, query **C5's collection**, `top_k` + filters; write retrieval log | §9.4 |
| C7 | Guardrails | `src/core/guardrails.py` | PII gate; §11 rule-ordered classifier; LLM-output post-checks (one citation ∈ retrieved, ≤3 sentences, no returns) | §7, §11 |
| C8 | LLM client | `src/core/llm_client.py` | Provider adapters (groq/gemini/openai/anthropic/mistral); strict-JSON mode; catalog check; retry/fallback | §9.5 |
| C9 | Answer composer | in `guardrails.py` + UI | Merge generation + evidence into final `AnswerCard`, incl. `Last updated from sources:` stamp | §7, §9.6 |
| C10 | UI (Phase 6) | `app/app.py` | Welcome line, 3 chips, disclaimer note, answer card, evidence expander, refusal card | §9.6 |
| C11 | Phase runner / CLI | `run.py` | `python run.py ingest` (Phases 1–3), `python run.py ask "<q>"` (4–5), `python run.py index ...` re-index | §17 |
| C12 | Goldens/eval | `evals/golden_questions.yaml`, `evals/run_evals.py` | 10 factual + 6 refusal questions; acceptance reporting | §14 |

## 3. Directory layout

```
mf-faq-assistant/
├── PRD.md · architecture.md · ProblemStatement.txt · README.md
├── requirements.txt · .env (.env.example committed only)
├── config.yaml                       # every changeable value (PRD §10)
├── prompts/system.prompt             # editable without code (PRD §9.5)
├── run.py                            # CLI: ingest | ask | index | evals
├── src/core/
│   ├── config.py   (C1)   # YAML + dotenv; validates on load
│   ├── loader.py   (C2)
│   ├── chunker.py  (C3)
│   ├── embedder.py (C4)
│   ├── vector_store.py (C5)
│   ├── retriever.py (C6)
│   ├── guardrails.py (C7, C9)
│   └── llm_client.py (C8)
├── app/app.py         (C10)
├── evals/
│   ├── golden_questions.yaml
│   └── run_evals.py   (C12)
├── data/                              # ← the RAG-demo evidence trail (PRD §9 preamble)
│   ├── sources.csv                    # curate-to-25 allowlist (GR-1)
│   ├── raw/            <label>.json   # Phase 1
│   ├── chunks/         chunks.jsonl · chunks_summary.csv   # Phase 2
│   ├── embeddings/     chunk_embeddings.npz                # Phase 3
│   ├── chroma/         persistent ChromaDB store           # Phase 3
│   └── retrieval/      q_*.json     # Phase 4 (one log per question)
└── deliverables/       sources.md · sample_qa.md · demo video link
```

Artifacts are **flat files / standard formats** (JSON, JSONL, NPZ, CSV) so every stage can
be opened and shown without tooling — this is the explicit "store each stage's data" demo
requirement, reflected as the storage map (§11).

## 4. Runtime stack & key choices (ADRs)

| # | Decision | Choice | Rationale | Alternatives rejected |
|---|---|---|---|---|
| A-1 | UI | Streamlit (single `app.py`) | Fastest path to chips + answer card + evidence expander; pure Python, zero build step | Static HTML (fine but slower to wire), Gradio |
| A-2 | Scraper | `requests` + `BeautifulSoup4` (+ `lxml`) | 5 known URLs; simple pages; robots-friendly; sync is enough | Playwright (overkill), trafilatura (weak heading/table fidelity) |
| A-3 | Chunking | Section-based + table fact strips | Preserves label/value semantics for table-styled fund pages; retrievable self-contained units | Fixed-size windows (fractures facts), sentence-only split |
| A-4 | Vector DB | ChromaDB `PersistentClient` | Zero-dependency local persistence; metadata filters; cosine | FAISS (no metadata store), Qdrant (extra server) |
| A-5 | Embedder | MiniLM-L6-v2 via `sentence-transformers` | PRD-mandated; 384-dim fits fact strips in 256-token window |
| A-6 | LLM access | OpenAI-compatible adapter first (Groq), adapters per provider | `.env`-driven swap of provider/model in 1 line; catalog-check warning | Per-provider hardcoding |
| A-7 | Guardrails placement | Rule-based **pre-LLM** gates + **post-LLM** deterministic checks | Gates never need the LLM (cheap, testable); post-checks enforce GR-4/5/3 mechanically | LLM-only self-policing |
| A-8 | LLM failure fallback | Extractive answer from top-1 chunk (template), still cited | Demo resilience when provider is down/JSON invalid; keeps demo honest | Raw crash, silent error |

## 5. Data contracts (schemas)

### 5.1 `data/raw/<label>.json`  — Phase 1 output

| Field | Type | Notes |
|---|---|---|
| `url`, `label` | string | from `config: scraping.pages` |
| `title` | string | `<title>` of the page |
| `fetched_at` | ISO-8601 (IST) | feeds the `Last updated from sources:` stamp (GR-6) |
| `http_status` | int | kept for source authenticity |
| `html`, `text` | string | raw + cleaned text (headings & tables preserved) |
| `source_notes` | string | e.g., "snapshot table extracted", freshness note |

### 5.2 `data/chunks/chunks.jsonl` — Phase 2 output (one JSON per line)

| Field | Type | Notes |
|---|---|---|
| `chunk_id` | `sha1(url ∥ section ∥ idx)` | stable across re-runs |
| `source_url` | string | **every** chunk has one (citations come from here, GR-4) |
| `scheme`, `category` | string | metadata filters (`scheme`, `category`) |
| `section` / `breadcrumb` | string | e.g., `About › Fund Snapshot › Expense ratio` |
| `kind` | enum | `section` \| `factstrip` |
| `text` | string | ≤ `chunk_chars_max` (1200); fact strips carry the context prefix |
| `char_count`, `token_count` | int | token count via MiniLM tokenizer (≤256 enforced by char cap) |
| `fetched_at` | ISO-8601 | inherited from page; feeds the answer stamp |

Also written: `data/chunks/chunks_summary.csv` (counts per page × section) for quick demo.

### 5.3 `data/embeddings/chunk_embeddings.npz` — Phase 3 output (inspection artifact)

`ids: str[] · vectors: float32[384] · meta: json` — ChromaDB is the **live store**; this NPZ
exists so embeddings can be eyeballed/diffed without opening Chroma (W3 demonstration).

### 5.4 ChromaDB record (internal to C5)

`collection = mf_faq_chunks · metadata = {"hnsw:space": "cosine"}`
documents = chunk text · metadatas = {`chunk_id, source_url, scheme, category, section, kind, fetched_at`} · ids = `chunk_id`.

### 5.5 `data/retrieval/q_<ts>.json` — Phase 4 log (RAG-demo artifact)

```json
{
  "ts": "2026-11-01T10:22:31+05:30",
  "question": "What is the ELSS lock-in period?",
  "filters": {"scheme": null, "category": null},
  "top_k": 5, "min_similarity": 0.35,
  "hits": [
    {"rank": 1, "chunk_id": "…", "score": 0.83, "url": "https://groww.in/…",
     "section": "About › Key Features", "kind": "factstrip", "text": "…"}
  ],
  "decision": {"kind": "retrieved_ok"}
}
```

### 5.6 LLM output contract (strict JSON; enforced, not trusted)

```json
{
  "type": "answer | refusal | out_of_scope | performance_redirect | pii",
  "answer": "≤3 sentences, derived ONLY from retrieved chunks",
  "citation_url": "must equal the URL of a retrieved hit (best chunk)",
  "refusal_link": "educational/official link for non-answer types",
  "quote": "short supporting snippet that justified the answer"
}
```

### 5.7 Final `AnswerCard` (UI payload; also the `sample_qa.md` row shape)

```json
{
  "question": "…",
  "type": "answer",
  "answer_text": "…",
  "citation_url": "…", "citation_title": "Groww — HDFC ELSS Tax Saver Fund (Direct, Growth)",
  "last_updated": "2026-11-01",           // max(fetched_at) across ingested pages
  "evidence": [ {"rank":1, "score":0.83, "url":"…", "section":"…"} ],
  "refusal_link": null
}
```

### 5.8 `data/sources.csv` (GR-1 allowlist)

`url, page_title, category, what_it_evidences, fetched_at, http_status`
grows from 5 → 15–25 rows; **all citations are validation-checked against this file.**

## 6. Flow A — Ingestion run (Phases 1–3, batch)

```
run.py ingest
   │  C1 config load + validate
   ▼
[C2 loader] ──for each scraping.pages────────────────────────────────────────────┐
   │ GET (UA, robots-check, timeout=30s, retry≤3/backoff)                        │  failure?
   ▼                                                                            ▼ record failure entry; continue
data/raw/<label>.json  ── all 5 fetched? ──no──▶ ABORT (no partial reindex)
   │ yes
   ▼
[C3 chunker] html → sections (H2/H3, breadcrumbs) + tables → fact strips
   │           drop returns/performance tables (GR-3); size discipline (max/min/overlap)
   ▼
data/chunks/chunks.jsonl + chunks_summary.csv
   ▼
[C4 embedder] MiniLM-L6-v2, batch=32, normalize → vectors (assert dim == 384)
   │
   ├──▶ data/embeddings/chunk_embeddings.npz          (inspection artifact)
   ▼
[C5 vector_store] PersistentClient(data/chroma) → recreate collection (idempotent)
   │                                                 upsert ids/documents/metadatas/embeddings
   ▼
[Consistency checks]  collection.count == len(chunks) · dim == 384 ·
                      every chunk_id present · sanity query ("expense ratio ELSS" in top-3)
```

Re-index is **idempotent and deterministic** (same chunks hash → same ids); deleting
`data/chroma/` then re-running `run.py ingest` (or `run.py index`) fully rebuilds.

## 7. Flow B — Question lifecycle (Phases 4–6, runtime)

### 7.1 Decision state machine (PRD §11 order is code order)

```
 question
    │
    ▼
 [PII gate regexes] ─yes▶ refuse (pii) — mask before ANY write; nothing stored
    │ no
    ▼
 [advisory?]  should I / buy / sell / hold / better / invest or / portfolio…
    │ yes ─▶ refusal(advisory) + edu link (AMFI / Mutual Funds Sahi Hai)
    ▼ no
 [performance-ask?] returns / CAGR / beat benchmark…
    │ yes ─▶ performance_redirect + that scheme's official factsheet link (no computing)
    ▼ no
 [in-scope?]  tracked AMC/schemes & process topics only
    │ no ─▶ refusal(out_of_scope) + AMC overview link
    ▼ yes
 [retrieve] embed(question) → ChromaDB query(top_k=5) → hits
    │ best score < min_similarity (0.35)
    │      └─▶ refusal(not_found) + best official page link (logged for corpus gaps)
    ▼ best score ≥ threshold
 [LLM generate] system prompt + hits (≤5×1200 chars ≈ ≤6k chars context)
    │ strict JSON (retry-once on parse fail) ─fail─▶ [A-8 extractive fallback from rank-1 hit]
    ▼
 [post-checks] citation ∈ retrieved URLs · exactly 1 link · ≤3 sentences ·
               no returns/claims · stamp present ─fail─▶ repair pass → extractive fallback
    ▼
 AnswerCard → UI   (+ retrieval & answer records appended under data/retrieval/)
```

### 7.2 Sequence (runtime happy path)

```
User → UI: click chip / type question
UI → PII gate: clean? → Classifier: "answer" path → Retriever:
        embed (MiniLM, same instance for process lifetime) → chroma.query(top_k=5)
        → write data/retrieval/q_<ts>.json
Retriever → LLM client (Groq): messages = [system.prompt, user(context=hits, question)]
LLM → strict JSON → post-checks → AnswerCard
UI ← AnswerCard: answer text · 1 citation link · "Last updated from sources: <date>"
                   · expandable evidence (top hits + scores) · refusal card for refusals
```

## 8. Guardrail enforcement points (GR-1…GR-8 → code sites)

| GR | Enforcement site | Mechanism |
|---|---|---|
| GR-1 official-only | `retriever.py` + composer post-check | hit URLs must be in `data/sources.csv` allowlist; capture hits at write time |
| GR-2 no PII | `guardrails.pii_gate()` | regex set (PAN, 12-digit Aadhaar, phone, email, OTP) fires **before** any persistence; redact on logs |
| GR-3 no performance | chunker drop-rule + classifier branch + post-check (no numbers-with-% patterns in answers) | triple enforcement |
| GR-4 one citation | composer | `citation_url` forced to best hit's URL; answer text contains exactly one link |
| GR-5 ≤3 sentences | post-check | sentence count; repair pass trims |
| GR-6 stamp | composer | `max(fetched_at)` of ingested pages; rendered under every answer |
| GR-7 safe refusal | classifier + templates | polite message + educational link (Appendix B URLs) |
| GR-8 UI note | `app.py` static block | always visible |

The user's question text is the only user input kept **in the session's retrieval log, after the PII gate**; nothing else persists. No chat history.

## 9. LLM provider abstraction (C8)

```python
class LLMClient(Protocol):
    def generate(self, messages: list[dict], *, model: str,
                 temperature: float, max_tokens: int,
                 response_json_schema: dict) -> str     # AIM: strict-JSON text
```

| Provider adapter | Trigger | Key var | Notes |
|---|---|---|---|
| `GroqClient` (default) | `LLM_PROVIDER=groq` | `GROQ_API_KEY` | OpenAI-compatible chat.completions; `model = GROQ_MODEL` (from `.env`) |
| `GeminiClient` / `OpenAIClient` / `AnthropicClient` / `MistralClient` | `LLM_PROVIDER` switch | per §10 `.env` | same interface; provider-specific JSON-mode mapping |

**Startup behavior:** read `LLM_PROVIDER` + key + model → if `startup_model_catalog_check=true`,
call provider's model-list endpoint and **warn (never crash)** if `GROQ_MODEL` id isn't found —
the id is corrected in `.env` only (ADR-6 / PRD §10 note).
**Failure chain:** missing key → fail fast with UI-visible message · 429/5xx → retry once →
bad JSON → one repair prompt → extractive fallback (A-8 classic extractive from rank-1 hit, still cited).

## 10. Configuration & startup checks (C1)

- Precedence: `config.yaml` values ← CLI overrides; secrets ← `.env`. Any PRD-listed
  changeable (chunking strategy/sizes, embedding model, vector DB path/collection/distance,
  `top_k`, provider/model/temperature) is config-only — **no code edits**.
- On boot (both pipelines): (1) YAML parses; (2) all required keys exist;
  (3) if reusing an existing collection: `count == len(chunks.jsonl)` and stored metadata dim == config `expected_dim`;
  (4) Phase 4 asserts its embedder + vector-store settings **equal** Phase 3's (same keys read, no divergence);
  (5) allowlist CSV present & non-empty.
- If embeddings model or chunking params change → intended flow is re-run `run.py ingest`
  (re-chunk + re-embed + recreate collection) — the mismatch check tells the operator.

## 11. Storage map (W3 delivery aid)

| Stage | Artifact | Is a "convince the viewer" record for |
|---|---|---|
| 1 Load | `data/raw/*.json` | Public sources only, per-page freshness timestamps |
| 2 Chunk | `data/chunks/chunks.jsonl` (+ CSV) | Chunking strategy, metadata citation coverage, no-returns guarantee |
| 3 Embed | `data/embeddings/*.npz` | 384-dim vectors, numbers |
| 3 Index | `data/chroma/` | Live vector DB, queryable locally |
| 4 Retrieve | `data/retrieval/q_*.json` | top-k plumbing, scores/URLs, decision path |
| 5 Generate | strict JSON + post-checks inside AnswerCard | One citation per answer, safe refusal behavior |
| 6 UI | Screenshot of answer card + evidence expander | Visible in the demo video or hosted prototype |

## 12. Error handling & resilience

| Failure | Behavior |
|---|---|
| A scrape fails | Retry ≤3 (backoff); if <5 pages succeed → **abort with clear message**, leave prior artifacts untouched |
| Chunker yields 0 chunks (page shape changed) | Abort; help points at raw JSON to inspect (never proceed with a stub) |
| Embedding count/dim mismatch | Assert-fail; show one-line remediation (`run.py ingest` to rebuild) |
| Chroma collection corrupted / stale | Recreate + reindex flag; never silently serve stale VDB |
| LLM provider unreachable / 429 / 5xx | Retry once → extractive fallback (A-8), still cited |
| LLM JSON invalid | One targeted repair prompt → fallback (A-8) |
| Citation post-check fails (mismatch/out-of-allowlist) | Repair once; if still bad → extractive fallback from best hit |
| PII detected | Refuse; **no persistence of raw question** (mask, then delete) |
| Question not found on tracked pages | Polite not-found refusal + official link; retained in `data/retrieval/` only (aggregated gap list) |

## 13. Non-functional envelope

- **Scale:** 5 pages → ~50–90 chunks → a few MB of artifacts; embedding/indexing seconds (CPU).
- **Latency budget (ask path):** embed ≈10–30 ms · Chroma query ≈50 ms · LLM ≈1–3 s → target **<4 s** end-to-end.
- **Privacy:** no chat history; single-turn; PII never stored (masked versions only where needed); retrieval logs carry question text only after gate; outbound calls go only to Groq (or the configured provider).
- **Reproducibility:** deterministic chunk ids; idempotent ingest; runbook in README; all artifacts re-generable from `run.py ingest`.

## 14. Deployment options

| Mode | How | Notes |
|---|---|---|
| **Local demo** | `streamlit run app/app.py` → `localhost:8501` · demo video from this | Recommended for the ≤3-min demo video; zero infra |
| **Notebook alternative** | `run.py` exposes `ask()` callable per phase for a notebook | Deliverable option 1 allows app/notebook |
| **Hosted** | Streamlit Community Cloud, secrets via dashboard; Chroma dir rebuilt on first boot (`run.py ingest` hook on `st.cache_resource`) | Watch: ephemeral filesystem → artifacts regenerate; keep artifacts committed where acceptable |
| Eval harness | `run.py evals` → acceptance report vs PRD §14 thresholds | Produces `evals/report.json` for submission |
| Runbook | `run.py ask "<q>"`, `run.py ingest`, `run.py evals` | Numbers to README §Setup |

## 15. Traceability — PRD → architecture

| PRD section | Architectural element |
|---|---|
| §7 guardrails GR-1…GR-8 | §8 enforcement table (guardrails.py + composer) |
| §9.1 Load | C2 loader.py + artifact 5.1 |
| §9.2 Chunking decision | C3 chunker.py + ADR A-3 + artifact 5.2 |
| §9.3 Embed + Chroma | C4/C5 + artifacts 5.3, 5.4 |
| §9.4 Retrieval (same model/DB) | C6 retriever.py + §10 startup asserts + artifact 5.5 |
| §9.5 LLM provider abstraction | C8 llm_client.py + provider table + §12 fallback |
| §9.6 Tiny UI | C10 app/app.py (welcome line, chips, note, expander) |
| §10 config contract | C1 config.py + `config.yaml` / `.env` models (§3 root files) |
| §11 decision logic | §7.1 state machine (classifier order = code order) |
| §12 sources | 5.8 sources.csv allowlist + GR-1 check |
| §14 eval acceptance | C12 `evals/run_evals.py` + PRD §14 golden/refusal sets |
| §17 milestones M0–M7 | Phases 1–6 mapping in §2 components |

## 16. Open implementation flags

1. Confirm Groq model id live (PRD §18 / startup catalog check covers it mechanically).
2. Determine the citation-preferred source (Groww help vs. CAMS/KFintech) for
   statement-download — priority order noted in `sources.csv` when finalised (PRD §18).
3. If hosted, verify Groww fetch is permitted (browsers vs serverless egress) — else
   commit pre-fetched artifacts from Phase 1 and skip live scraping on hosting (standalone
   ingest remains the local path).
