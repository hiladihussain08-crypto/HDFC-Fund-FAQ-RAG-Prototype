"""Vercel serverless function: POST /api/ask  { "question": "..." }."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Vercel gives a read-only filesystem except /tmp. Point the model cache there.
os.environ.setdefault("HF_HOME", "/tmp/hf")
os.environ.setdefault("TRANSFORMERS_CACHE", "/tmp/hf")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import load_config
from src.query.pipeline import answer_question

app = FastAPI(title="HDFC MF FAQ API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(req: AskRequest):
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    try:
        config = load_config()
        config.ensure_dirs()
        response = answer_question(question, config, persist=False)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="pipeline error") from exc
    return response


@app.get("/health")
def health():
    return {"status": "ok"}