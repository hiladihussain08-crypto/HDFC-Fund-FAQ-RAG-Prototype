"""Tests for the FastAPI service (api/main.py)."""

from __future__ import annotations

import os

# Configure env BEFORE importing the app module (it reads API_KEY at import).
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("WRITE_ARTIFACTS", "false")

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

client = TestClient(app)
HEADERS = {"X-API-Key": "test-api-key"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_factual_question():
    r = client.post(
        "/ask",
        json={"question": "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "factual"
    assert "1.02%" in data["answer"]
    assert data["hero"] is not None
    assert data["hero"]["value"] == "1.02%"
    assert data["hero"]["context"] == "Base expense ratio 0.84%"
    assert data["source_url"] is not None
    assert data["last_updated"] is not None
    assert data["meta"]["query_id"]
    assert isinstance(data["meta"]["chunks"], list)


def test_hero_context_null_for_non_expense():
    r = client.post(
        "/ask",
        json={"question": "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "factual"
    assert data["hero"] is not None
    assert data["hero"]["context"] is None


def test_advice_question_refused():
    r = client.post(
        "/ask",
        json={"question": "Should I invest in HDFC Large Cap Fund?"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "refused"
    assert data["hero"] is None


def test_unknown_fund_not_found():
    r = client.post(
        "/ask",
        json={"question": "What is the expense ratio of SBI Bluechip Fund?"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "not_found"


def test_clarify_no_fund():
    r = client.post(
        "/ask",
        json={"question": "How much is the minimum sip?"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "clarify"
    assert data["hero"] is None
    assert data["fund_name"] is None
    assert data["source_url"] is None
    assert data["last_updated"] is None
    assert data["intent"] == "min_sip"
    assert isinstance(data.get("options"), list)
    assert len(data["options"]) == 4
    assert "HDFC Large Cap Fund Direct Growth" in data["options"]


def test_missing_api_key_401():
    r = client.post(
        "/ask",
        json={"question": "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"},
    )
    assert r.status_code == 401


def test_oversized_question_4xx():
    r = client.post(
        "/ask",
        json={"question": "x" * 301},
        headers=HEADERS,
    )
    assert r.status_code == 422  # validation error (bad input)