"""FastAPI service exposing the HDFC MF FAQ RAG pipeline over HTTP.

Deployed on Hugging Face Spaces (Docker SDK) and runnable locally with
``uvicorn api.main:app --host 0.0.0.0 --port 7860``.
"""

from __future__ import annotations

import os
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("HF_HOME", "/tmp/hf")
os.environ.setdefault("TRANSFORMERS_CACHE", "/tmp/hf")

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import load_config
from src.query.pipeline import answer_question
from src.schemes import SCHEME_BY_ID
from src.ui.styles import inject as _inject  # noqa: F401 (kept for parity)

app = FastAPI(title="HDFC MF FAQ API", version="1.0.0")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
_origins_raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
_allowed_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
_API_KEY = os.environ.get("API_KEY", "")


def require_api_key(request: Request) -> None:
    if not _API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized.")
    supplied = request.headers.get("X-API-Key", "")
    if supplied != _API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized.")


# ---------------------------------------------------------------------------
# Rate limit (in-memory, 20 req/min per IP)
# ---------------------------------------------------------------------------
_RATE_LIMIT = 20
_WINDOW_SECONDS = 60.0
_buckets: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _buckets[client_ip]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")
    bucket.append(now)


# ---------------------------------------------------------------------------
# Startup: warm the model + Chroma client once
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _warmup() -> None:
    try:
        config = load_config()
        config.ensure_dirs()
        from src.embedding import get_model

        get_model(config)
        # open the collection once so the first request is fast
        import chromadb

        client = chromadb.PersistentClient(path=str(config.chroma.persist_dir))
        client.get_collection(config.chroma.collection)
    except Exception:  # noqa: BLE001
        # Don't crash startup; the request path will surface a clean error.
        pass


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=300)


_HERO_RE = None


def _hero_regex():
    global _HERO_RE
    if _HERO_RE is None:
        import re

        _HERO_RE = re.compile(r"(₹\s?[\d,]+(?:\.\d+)?|\d[\d,]*\.?\d*\s*%)")
    return _HERO_RE


def _extract_hero(answer: str):
    m = _hero_regex().search(answer)
    if not m:
        return None, None
    hero = m.group(0).strip()
    import re

    pm = re.search(r"\(([^)]+)\)", answer)
    secondary = pm.group(1).strip() if pm else None
    return hero, secondary


_INTENT_LABEL = {
    "expense_ratio": "Expense ratio",
    "exit_load": "Exit load",
    "min_sip": "Minimum SIP",
    "min_investment": "Minimum investment",
    "fund_manager": "Fund manager",
    "fund_house": "Fund house",
    "aum": "AUM",
    "category": "Category",
    "lock_in": "Lock-in",
    "riskometer": "Riskometer",
    "benchmark": "Benchmark",
    "launch_date": "Launch date",
    "stamp_duty": "Stamp duty",
}


def _map_status(route: str) -> str:
    if route == "answer":
        return "factual"
    if route and route.startswith("refuse"):
        return "refused"
    if route == "miss":
        return "not_found"
    return "error"


def _last_updated_date(last_updated: str):
    import re

    m = re.search(r"\d{4}-\d{2}-\d{2}", last_updated or "")
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ask")
def ask(req: AskRequest, _auth=Depends(require_api_key), _rl=Depends(rate_limit)):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        config = load_config()
        config.ensure_dirs()
        response = answer_question(question, config, persist=False)
    except Exception:  # noqa: BLE001
        return {
            "status": "error",
            "answer": "Something went wrong while answering. Please try again.",
            "hero": None,
            "fund_name": None,
            "intent": None,
            "source_url": None,
            "last_updated": None,
            "meta": {"mode": "error", "latency_ms": 0, "query_id": "", "chunks": []},
        }

    route = response.get("route", "")
    status = _map_status(route)
    answer = response.get("answer", "")

    hero = None
    if status == "factual":
        hero_val, secondary = _extract_hero(answer)
        if hero_val:
            intent = response.get("intent", "other")
            hero = {
                "label": _INTENT_LABEL.get(intent, intent.replace("_", " ").title()),
                "value": hero_val,
                "context": secondary,
            }

    fund_name = None
    scheme_id = response.get("scheme", "")
    if scheme_id and scheme_id in SCHEME_BY_ID:
        fund_name = SCHEME_BY_ID[scheme_id].name

    intent = response.get("intent")
    if intent in (None, "", "other"):
        intent = None

    chunks = []
    for hit in response.get("hits", []) or []:
        chunks.append({"text": hit.get("text", ""), "source": hit.get("source_url", "")})

    payload: dict[str, Any] = {
        "status": status,
        "answer": answer,
        "hero": hero,
        "fund_name": fund_name,
        "intent": intent,
        "source_url": response.get("citation_url") or None,
        "last_updated": _last_updated_date(response.get("last_updated", "")),
        "meta": {
            "mode": (response.get("generation") or {}).get("mode", "policy"),
            "latency_ms": response.get("latency_ms", 0),
            "query_id": response.get("query_id", ""),
            "chunks": chunks,
        },
    }
    return payload