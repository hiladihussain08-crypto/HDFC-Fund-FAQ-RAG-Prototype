# PRD — Mutual Fund FAQ Assistant (Facts-Only RAG)

> **Source document:** [`ProblemStatement.txt`](./ProblemStatement.txt)
> Usually phrased as "*Small FAQ assistant for mutual fund scheme facts on Groww pages —
> facts only, one citation per answer, no advice.*"

| | |
|---|---|
| **Product** | MF FAQ Assistant — HDFC Mutual Fund (AMC overview + 5 scheme pages) |
| **Type** | Small-corpus RAG prototype + tiny chat UI |
| **Version / Status** | 1.0 — Draft, ready for build |
| **Date** | 2026-11-01 |
| **Derivation** | `ProblemStatement.txt` + requester implementation notes (phase-wise RAG, MiniLM, ChromaDB, Groq/qwen, config-driven) |
| **Primary skill targets** | W1 (Thinking Like a Model), W2 (LLMs & Prompting), W3 (RAGs only) |

---

## 1. Summary

A small, citations-first FAQ assistant that answers **factual** questions about HDFC
Mutual Fund schemes — expense ratio, exit load, minimum SIP, lock-in (ELSS), riskometer,
benchmark, and how to download statements — using only **official public pages**
(Groww AMC + scheme pages, supported by SEBI/AMFI/AMC official pages). Every answer shows
**exactly one source link**, stays ≤3 sentences, and carries a
**"Last updated from sources: …"** stamp. Opinionated/portfolio questions are politely
refused with an educational link. Built phase-wise as an explicit RAG demo:
**Load → Chunk → Embed → Retrieve → Generate**, with per-stage artifacts stored on disk
so each stage can be shown to graders. No advice, no PII, no performance claims.

## 2. Problem

Retail investors and support staff ask the same repetitive mutual-fund questions
("What's the expense ratio?", "What is ELSS's lock-in?", "How do I get a capital-gains
statement?") and almost every existing tool drifts into **advice**, **performance
hedging**, or **uncited marketing copy**. There is no tiny, transparent, facts-only
assistant restricted to official pages where every answer traces to one verifiable URL.

## 3. Users

| Persona | Need | Outcome |
|---|---|---|
| **Retail user comparing schemes** | Quick, trustworthy facts on one AMC's schemes while researching | Direct answer + 1 official link, no selling, no jargon |
| **Support / content team member** | Reuse-safe answers to repetitive MF questions with citable source | Copy-ready answer + citation; consistent refusal handling |

## 4. Goals & success criteria

| # | Goal | Success measure |
|---|---|---|
| G1 | Working prototype answers factual MF questions from a small scraped corpus | ≥90% of the 10 golden factual questions answered correctly with a working citation |
| G2 | Every answer carries exactly one clear official citation link | 100% (zero answers without citation) |
| G3 | Advisory/opinion questions are safely refused (polite + educational link) | 100% of refusal-set questions refused; zero advisory answers |
| G4 | Answers are concise and transparent | ≤3 sentences; "Last updated from sources:" shown on 100% of answers |
| G5 | Each RAG stage's data is stored explicitly (RAG demo) | Raw / chunks / embeddings / vector DB / retrieval logs all exist as artifacts and are viewable |
| G6 | Pipeline behaviour changeable without code edits | Embedding model, chunking params, vector DB, top-k, LLM model all live in `config.yaml` / `.env` |

## 5. Non-goals (explicit)

- **No investment advice or recommendations** (no "should I buy/sell/hold", no suitability).
- **No performance claims** — returns are never computed, compared, or summarised; redirect to official factsheet.
- **No PII handling** — PAN, Aadhaar, account numbers, OTPs, emails, phone numbers are refused and never stored.
- No other AMCs / schemes / asset classes (equity stocks, insurance, FDs) — out of scope refusals.
- No multi-turn memory, no admin panel, no analytics dashboards.
- No scraping of Groww's app back-end or any private endpoint; demo media shows the public UI and our own pipeline artifacts only.

## 6. Content scope

### 6.1 Primary pages to scrape & store (Phase 1 targets)

| # | Page | URL |
|---|---|---|
| 1 | AMC overview — HDFC Mutual Fund | `https://groww.in/mutual-funds/amc/hdfc-mutual-funds` |
| 2 | Large Cap — HDFC Large Cap Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth` |
| 3 | Flexi Cap — HDFC Flexi Cap Direct Plan Growth | `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth` |
| 4 | ELSS — HDFC ELSS Tax Saver Fund Direct Plan Growth | `https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth` |
| 5 | Mid Cap — HDFC Mid Cap Fund Direct Growth | `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth` |

### 6.2 In-scope FAQ topics

Scheme facts (expense ratio, exit load, minimum SIP/investment, NAV date reported on the page,
benchmark index, category, fund manager, riskometer bucket as published), AMC facts
(name, launch info, schemes count), ELSS specifics (3-year lock-in), and the **process
how-to** for capital-gains/transaction statement download (statement source pages).
Definitions (e.g., "what is a riskometer?") are answered from SEBI/AMFI official pages.

## 7. Guardrails (must-pass hard rules)

| # | Rule | Implementation |
|---|---|---|
| GR-1 | **Public sources only** — citations point to official public pages (Groww surfaces, SEC-registered AMC site, SEBI, AMFI, CAMS/KFintech). No third-party blogs; no app back-end screenshots. | Source allowlist in `data/sources.csv`; retrieval citations filter on this list |
| GR-2 | **No PII accepted/stored** — PAN, Aadhaar, account no., OTP, email, phone | Input regex gate fires **before** any logging/persistence; masked refusal message; retrieval/request logs store only the question text pattern-flagged redact |
| GR-3 | **No performance claims** — never compute/compare returns | Prompt prohibition + post-check; performance-style questions get the official factsheet link instead |
| GR-4 | **One citation per answer** — a single, clear, clickable source link | Answer JSON forces exactly one `citation_url`; UI renders it as the answer's link |
| GR-5 | **Concise** — answer body ≤3 sentences | Prompt instruction + length post-check (sentence count) |
| GR-6 | **Transparency** — "Last updated from sources: <date>" on every answer | Stamp = latest `fetched_at` among all source pages |
| GR-7 | **Safe refusal** — advisory/opinion/out-of-scope questions refused politely with a relevant educational link | Classifier rules (§11) + refusal templates (Appendix B) |
| GR-8 | **Facts-only UI note** — "Facts-only. No investment advice." always visible | Static header/footer element in UI |

## 8. Architecture

```
        config.yaml / .env  (embedding model, chunk params, vector DB, top-k, LLM provider+model)
                       │  drives every phase below
                       ▼
 Part A — Ingestion pipeline
   [1 Data Loading]  →  data/raw/*.json
   [2 Data Chunking] →  data/chunks/chunks.jsonl
   [3 Embedding + Vector DB] → data/embeddings/chunk_embeddings.npz + ChromaDB persistent store
                       │
 Part B — Q&A pipeline
   [4 Data Retrieval] → data/retrieval/*.json (same embedder + same ChromaDB)
   [5 Generation LLM] → Groq (or Gemini/OpenAI/Anthropic/Mistral) with strict prompt
   [6 Tiny UI]        → welcome line + 3 example questions + "Facts-only. No investment advice."
```

## 9. RAG pipeline requirements (phase-wise)

> Each phase stores its stage data explicitly on disk — this is the RAG-demo evidence trail
> (implementation-notes requirement) and every artifact must be human-viewable.

### Phase 1 — Data Loading

**Objective:** fetch and store the 5 primary pages as clean, machine-readable JSON.

- Scrape all URLs from `config: scraping.pages` (the 5 Groww pages, §6.1).
- One artifact per page: `data/raw/<label>.json` with fields:
  `url, label, title, fetched_at (ISO-8601, IST), http_status, html, text, source_notes`.
- Fetch with a descriptive `user_agent` declared in config; respect `robots.txt`;
  single run-friendly script (`1_load.py`), re-runnable, no PII in artifacts.
- Text extraction drops nav/footer widget noise but **keeps headings + tables** (they carry
  the fact values needed downstream).
- **Acceptance:** 5 raw JSON files; every file has `fetched_at`; text version contains the
  scheme name and key facts (spot-check: expense ratio, exit load, min SIP strings present).

### Phase 2 — Data Chunking — *strategy owned by the AI coding agent, decided from the data*

**Decision (recorded for review):** these 5 page types are short, highly structured, and
fact-dense → **semantic, section-based chunking with table-aware "fact strips"**:

1. **Section chunks** — split cleaned text at heading boundaries (H2/H3), keeping
   heading breadcrumbs ("Fund Overview › About") for context.
2. **Table fact strips** — key-value tables (Fund Snapshot, etc.) become one atomic strip
   per logical row-group with a context prefix, e.g.
   *"Scheme: HDFC ELSS Tax Saver Fund (Direct-Growth) | Section: Fund snapshot |
   Expense ratio: …; Exit load: …; Min SIP: …"* — so no value ever floats context-free.
3. **Size discipline** — `chunk_chars_max = 1200` (~300 words, below MiniLM's 256-token
   window), `overlap_chars = 120`, drop chunks under `chunk_chars_min` (noise).

**Why not fixed-size splitting?** Fixed-size windows fracture table rows and label/value
pairs across chunks → retrieval returns half-facts and citations to the wrong section. For
a 5-page corpus, full semantic-section + fact-strip chunking preserves retrievability and
makes citations precise. (Fixed-size and recursive strategies remain selectable in
`config: chunking.strategy` for future corpora.)

**Every chunk carries metadata:** `chunk_id, source_url, scheme, category, section,
char_count, token_count, fetched_at`. **No chunk ever contains a returns/performance table.**
- Artifact: `data/chunks/chunks.jsonl` (one JSON per line) + `chunks_summary.csv` (counts per page/section).
- **Acceptance:** 100% of chunks have `source_url`; each fact strip is self-contained; no
  chunk > `chunk_chars_max`.

### Phase 3 — Data Embedding + Vector DB (indexing)

**Objective:** embed all chunks and store them in ChromaDB.

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim), `normalize = true`,
  `batch_size = 32` — all from config.
- Vector DB: **ChromaDB** `PersistentClient(path = config.vector_db.persist_dir)`,
  collection `mf_faq_chunks`, distance metric **cosine** — all from config.
- Artifacts (both kept):
  - `data/embeddings/chunk_embeddings.npz` — `ids, vectors, metadata` for direct inspection;
  - ChromaDB persistent directory `data/chroma/` — the live queryable index.
- Store each chunk's **text and metadata** alongside the vector in ChromaDB so retrieval
  returns text + `source_url` directly.
- **Acceptance:** collection count == chunk count; vectors are 384-dim (asserted);
  sanity check: query "expense ratio ELSS" hits the ELSS fact strip in top 3.

### Phase 4 — Data Retrieval

**Objective:** retrieve the best evidence chunks for a user query.

- **Same embedding model and same vector DB as ingestion** — guaranteed by reading the
  identical config keys; startup assert validates config identity.
- Query flow: embed query → ChromaDB query with `top_k` (default 5) and optional metadata
  filters (`scheme`, `category`) → returns chunk text + score + `source_url`.
- Similarity floor `min_similarity` to avoid junk evidence.
- Artifact: one JSON per question in `data/retrieval/` — `question, query_embedding_id,
  top_chunks[{chunk_id, score, url, section, text_snippet}]` — shown in the UI's
  evidence expander and demo-able on its own.
- **Acceptance:** for the 10-question golden set, the correct fact-bearing chunk lands in
  top-3 with a valid allowlisted URL.

### Phase 5 — Answer generation (LLM)

**Objective:** turn retrieved evidence into the final ≤3-sentence cited answer or refusal.

- **Provider abstraction** — provider selection via `LLM_PROVIDER` in `.env`:
  | Provider | Priority | API key var | Notes |
  |---|---|---|---|
  | **Groq (primary)** | default | `GROQ_API_KEY` | OpenAI-compatible endpoint; model from `GROQ_MODEL` |
  | Gemini | optional swap | `GEMINI_API_KEY` | |
  | OpenAI | optional swap | `OPENAI_API_KEY` | |
  | Anthropic | optional swap | `ANTHROPIC_API_KEY` | |
  | Mistral | optional swap | `MISTRAL_API_KEY` | |
- **Model id comes from `.env` only** (`GROQ_MODEL`, default `qwen/qwen3.8-27b`).
  ⚠️ *Model-id note:* the exact id must match the provider's public model list — the app
  runs a **startup catalog check** and warns (never crashes silently) if the configured id
  is not found, so the id can be corrected in `.env` with no code change.
-	System prompt (configurable file `prompts/system.prompt`): facts-only; use retrieved
  chunks as sole evidence; ≤3 sentences; exactly one citation link (the best retrieved
  chunk's URL); refuse advisory/opinion/out-of-scope per templates; never compute returns;
  never invent numbers; output strict JSON: `answer, citation_url, type
  (answer|refusal|out_of_scope|performance_redirect|pii), refusal_link`.
- Low temperature (0.2, config), retry-once on provider errors, fail-fast if no API key.
- **Acceptance:** 100% answers parse; exactly one link; ≤3 sentences; refusal types return
  the specified educational link.

### Phase 6 — Tiny UI

**Objective:** minimal, clear Q&A surface (single page).

- Welcome line, e.g. *"Hi! I answer facts about HDFC Mutual Fund schemes on Groww pages —
  with sources."*
- **3 example question chips** (click to ask):
  1. *"What is the expense ratio of HDFC Large Cap Fund (Direct, Growth)?"*
  2. *"What is the lock-in period for HDFC ELSS Tax Saver Fund?"*
  3. *"How do I download my capital-gains statement?"*
- Prominent static note: **"Facts-only. No investment advice."**
- Answer card: answer text (≤3 sentences) + **one citation link** +
  `Last updated from sources: <date>`.
- Evidence expander (▶) revealing the top retrieved chunks + scores + URLs — the RAG demo moment.
- Refusal card with polite message + educational link. No chat history persistence.

## 10. Configuration contract ("to be changed" without code edits)

### `config.yaml`

```yaml
project: mf-faq-assistant-rag

paths:                                  # runtime file — stage inputs/outputs
  raw_dir: data/raw
  chunks_file: data/chunks/chunks.jsonl
  embeddings_file: data/embeddings/chunk_embeddings.npz
  vector_db_dir: data/chroma
  retrieval_log_dir: data/retrieval
  sources_file: data/sources.csv

scraping:
  pages:                                # Phase 1 target list (edit to add/remove pages)
    - label: amc_overview
      url: https://groww.in/mutual-funds/amc/hdfc-mutual-funds
    - label: hdfc_large_cap_fund_direct_growth
      url: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
    - label: hdfc_flexi_cap_fund_direct_growth
      url: https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
    - label: hdfc_elss_tax_saver_fund_direct_plan_growth
      url: https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
    - label: hdfc_mid_cap_fund_direct_growth
      url: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
  user_agent: "mf-faq-rag-demo/1.0 (educational)"
  respect_robots_txt: true
  timeout_seconds: 30

chunking:
  strategy: section_semantic_table_factstrips   # decided for this data; switchable
  chunk_chars_max: 1200                         # ≈300 words, under MiniLM 256-token window
  chunk_chars_min: 120
  overlap_chars: 120
  tables_as_fact_strips: true

embedding:
  model: sentence-transformers/all-MiniLM-L6-v2  # used by Phase 3 AND Phase 4
  normalize: true
  batch_size: 32
  expected_dim: 384

vector_db:
  provider: chroma
  persist_dir: data/chroma                       # PersistentClient(path=persist_dir)
  collection: mf_faq_chunks
  distance: cosine                               # metadata={"hnsw:space":"cosine"}

retrieval:
  top_k: 5
  min_similarity: 0.35
  metadata_filters: [scheme, category]

llm:
  provider: groq                                 # groq|gemini|openai|anthropic|mistral
  temperature: 0.2
  max_tokens: 400
  system_prompt_file: prompts/system.prompt
  startup_model_catalog_check: true              # warn if .env model id not in provider list
```

### `.env` (never committed; `.env.example` shipped)

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=<your-key>
GROQ_MODEL=qwen/qwen3.8-27b
# Optional — only needed if LLM_PROVIDER changes:
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
MISTRAL_API_KEY=
```

**Principles:** changing embedding model, chunk strategy/size, vector DB path/collection,
top-k, or LLM provider/model/timezone-stamp happens only in `config.yaml` / `.env`.
Changing the embedding model or collection requires a one-command re-index
(re-runs Phases 3) — enforced by a `chunk_count == collection_count` consistency check.

## 11. Answer-vs-refuse decision logic (W1 focus)

Order of evaluation on every incoming question:

1. **PII present?** (PAN pattern `AAAAA9999A`, 12-digit Aadhaar, 10-digit phone, email,
   OTP/disguised bank-acct keywords) → **refuse + no persistence of the raw question**
   (mask before any log): *"For your privacy I don't handle personal details — you don't
   need to share them to get scheme facts."*
2. **Advisory/opinion?** ("should I", "buy/sell/hold", "is it a good time", "better than",
   "portfolio fit", "invest or not") → **safe refusal** + educational link (AMFI investor
   education portal, `mutualfundssahihai.com` / AMFI official page): *"I can share facts
   only, not advice. For decisions, please consult a SEBI-registered investment adviser."*
3. **Performance/returns asked?** ("returns of last year", "CAGR", "did it beat benchmark")
   → **facts-only redirect** to that scheme's **official factsheet link** (no computation).
4. **Out of scope?** (other AMCs, stocks, insurance) → scope statement + link back to
   the AMC overview page analysed.
5. **Factual & in-scope** → retrieve → if best chunk score ≥ `min_similarity`, answer;
   else: *"I couldn't find that fact on the tracked official pages"* + link to the relevant
   official page/search, and log for corpus expansion.

## 12. Sources (curated, 15–25 official URLs)

| Category | Count | Examples | Evidence |
|---|---|---|---|
| Groww scheme/AMC pages | 5 | the 5 URLs in §6.1 | scheme facts, snapshot tables |
| Groww official help / how-to pages | 2–4 | statement & capital-gains statement download help pages | process how-to answers |
| HDFC AMC official (`hdfcfund.com`) | 4–6 | per-scheme fund pages + factsheets + ELSS features | cross-verification, factsheet redirect targets |
| SEBI official | 2–3 | riskometer circular/page, investor education | riskometer definition |
| AMFI official | 2–3 | NAV/data definitions, `mutualfundssahihai.com` education pages | definitions, educational refusal link |
| CAMS / KFintech official | 1–2 | statement services pages | statement download how-to |

Output: `data/sources.csv` (and `deliverables/sources.md`) —
`url, page_title, category, what_it_evidences, fetched_at, http_status`.
Target total: **15–25 URLs**, official public pages only (GR-1).

## 13. Deliverables checklist

- [ ] Working prototype (hosted app/notebook link) **or** ≤3-min demo video showing: ask → cited answer → refusal on an advisory question → evidence expander showing chunk artifacts.
- [ ] `deliverables/sources.md` + `data/sources.csv` — the 15–25 official URLs.
- [ ] `README.md` — setup steps, scope (AMC + 5 schemes), phase runs (1→3), known limits.
- [ ] `deliverables/sample_qa.md` — 5–10 queries with the assistant's answers + citation links (format in Appendix C).
- [ ] Disclaimer snippet (Appendix A) shown in UI and included in README.

## 14. Evaluation & acceptance (mapped to tested skills)

**Golden factual set (10):** expense ratio (Large Cap, ELSS), ELSS lock-in, min SIP
(Large Cap, Mid Cap), exit load (Flexi Cap), benchmark (Mid Cap), riskometer (ELSS),
AMC overview fact, statement-download how-to.

**Refusal set (6):** "Should I buy HDFC Large Cap now?", "Which is better — Mid Cap or
Flexi Cap?", "How did the fund perform last year?" (→ factsheet redirect), "My PAN is…
what's my expense ratio?" (→ PII refuse, nothing stored), "Best Index fund?" (out of
scope), "Should I invest ₹5L in ELSS for tax?" (advisory).

| Skill | Tested behavior | Acceptance |
|---|---|---|
| W1 — Thinking like a model | Exact-fact identification; answer vs. refuse decisions | factual set ≥90% correct; refusal set 100% correctly refused + educational link; 0 advisory answers |
| W2 — LLMs & prompting |Instruction style, concise phrasing, polite refusals, citation wording | 100% answers ≤3 sentences with exactly 1 citation; refusals polite and consistently formatted; `Last updated:` stamp on 100% |
| W3 — RAGs only | small-corpus retrieval with accurate citations | correct chunk in top-3 for ≥90% golden queries; 100% citations resolve to allowlisted official URLs; all 5 stage artifacts present (raw / chunks / embeddings / Chroma / retrieval logs) |

## 15. Known limits (for README)

- Corpus = 3-listed-page scope only; other AMC/schemes out of scope.
- Scheme facts sourced from Groww surfaces; cross-checked on hdfcfund.com where relevant — answers cite one link per answer even though two sources may agree.
- MiniLM embeddings struggle on rare wording/synonyms → mitigated with fact-strip chunks; not a guarantee.
- Groww DOM changes or rate limits → re-run Phase 1; keep delays if throttled.
- LLM catalog changes (model id) → fix `.env`, no code change (GROQ_MODEL + catalog startup check warn-on-mismatch).
- No chat history; single-turn only by design (privacy).

## 16. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Groww page DOM/layout change | Medium | breaks extraction | config re-list + re-run Phase 1–3; keep raw JSON for re-chunking without re-scrape |
| Rate limiting / bot detection on scrape | Low | medium | respect robots.txt, descriptive UA, bounded timeout, cache first successful pull |
| LLM invents source or facts | Medium | high | citation force-constrained to retrieved chunk URL (never LLM's own), post-check link ∈ retrieved set |
| `qwen/qwen3.8-27b` id not available on provider | Medium | low | `.env`-driven; startup catalog check surfaces mismatch; swap id in `.env` |
| Answers drift into advice on edge queries | Medium | high | §11 rule-order classifier + refusal templates + prompt hard rules + eval set |
| PII sneaks into logs | Low | high | gate runs before any write; pattern tests in acceptance |

## 17. Milestones

| # | Milestone | Exit criteria |
|---|---|---|
| M0 | Finalize 15–25 source list | `data/sources.csv` complete, all official |
| M1 | Phase 1 load done | 5 raw JSONs with `fetched_at` |
| M2 | Phase 2 chunking done | `chunks.jsonl`, metadata-covers-all, size limits pass |
| M3 | Phase 3 embed+index done | Chroma count == chunks, 384-dim, sanity query passes |
| M4 | Phase 4 retrieval done | retrieval logs exist; top-3 hit-rate on golden set ≥90% |
| M5 | Phase 5 generation done (Groq + .env) | strict JSON answers, cited, ≤3 sentences; refusal paths live |
| M6 | Phase 6 UI done | welcome line, 3 chips, disclaimer, evidence expander |
| M7 | Deliverables packaged | prototype/video, sources, README, sample_qa, disclaimer — all present |

## 18. Open questions

1. Hosting vs. demo video — confirm by M5 (deliverable allows either).
2. Confirm statement-download should cite a Groww help page vs. CAMS/KFintech (may matter per user's app).
3. Exact final Groq model id must be validated live (see §10 note + §16 risk).

---

## Appendix A — Disclaimer snippet (UI)

> **Facts-only. No investment advice.**
> This assistant shares publicly available scheme facts (e.g., expense ratio, exit load,
> minimum SIP, lock-in, riskometer, benchmark) with one source link per answer.
> It does not recommend, advise, or predict — please read all scheme related documents
> carefully before investing. Mutual fund investments are subject to market risks.

*(Each answer also ends with:)* `Last updated from sources: <YYYY-MM-DD>`

## Appendix B — Refusal templates (polite, always with a link)

| Case | Template |
|---|---|
| Advisory / buy-sell | "That's an advice question, and I only share facts. For whether this fits your portfolio, please talk to a SEBI-registered investment adviser. Helpful basics: [AMFI investor education](https://www.amfiindia.com/) / [Mutual Funds Sahi Hai](https://www.mutualfundssahihai.com/)" |
| Performance claim | "I don't compute or compare returns. The fund's official factsheet has performance data: [factsheet link]" |
| PII | "For privacy I never accept or store PAN/Aadhaar/account/OTP/email/phone. You don't need them for scheme facts — ask me any fact question." |
| Out of scope | "I only cover the tracked HDFC Mutual Fund pages on Groww. Here's the tracked scope: [AMC overview page]" |
| Fact not found | "I couldn't find that fact on the tracked official pages. Best place to check: [official page]" |

## Appendix C — sample_qa.md row format

| Field | Value (example) |
|---|---|
| **Q** | "What is the ELSS lock-in period?" |
| **A** | "Equity Linked Savings Schemes (ELSS) have a mandatory lock-in of 3 years. HDFC ELSS Tax Saver Fund is an ELSS scheme, so its units are locked in for 3 years from the date of allotment." |
| **Citation** | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| **Last updated from sources** | 2026-11-01 |
| **Type** | answer |
