"""Vercel serverless function: GET /api  (health / info)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("HF_HOME", "/tmp/hf")
os.environ.setdefault("TRANSFORMERS_CACHE", "/tmp/hf")

from fastapi import FastAPI

app = FastAPI(title="HDFC MF FAQ API")

@app.get("/")
def root():
    return {"name": "HDFC MF FAQ RAG", "status": "ok", "endpoints": ["/api/ask", "/api/health"]}