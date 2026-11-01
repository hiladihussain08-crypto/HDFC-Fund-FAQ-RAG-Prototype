"""Provider adapter for the generation step (Groq by default).

Only the selected provider's key is required.  Missing key / network failure is
returned as an error so the caller can fall back to extractive answering.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from src.config import LlmConfig

OPENAI_COMPATIBLE_BASE = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "mistral": "https://api.mistral.ai/v1",
}


@dataclass
class LlmResponse:
    text: str
    provider: str
    model: str
    raw: dict | None
    error: str | None
    latency_ms: int


def _post(url: str, payload: dict, headers: dict, timeout: int) -> tuple[dict | None, str | None]:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            if response.status_code >= 400:
                return None, f"http_{response.status_code}: {response.text[:300]}"
            return response.json(), None
    except httpx.HTTPError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def call_llm(system: str, user: str, config: LlmConfig) -> LlmResponse:
    provider = config.provider.lower()
    started = time.perf_counter()

    if provider == "extractive":
        return LlmResponse("", provider, "extractive", None, "provider=extractive", 0)

    if not config.api_key:
        return LlmResponse(
            "", provider, config.model, None, f"missing_api_key ({provider.upper()}_API_KEY)", 0
        )

    if provider in OPENAI_COMPATIBLE_BASE:
        url = f"{OPENAI_COMPATIBLE_BASE[provider]}/chat/completions"
        payload = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        headers = {"Authorization": f"Bearer {config.api_key}"}
        raw, error = _post(url, payload, headers, config.timeout_seconds)
        text = ""
        if raw:
            try:
                message = raw["choices"][0]["message"]
                text = (message.get("content") or "").strip()
                if not text and message.get("reasoning"):
                    error = "empty_content_with_reasoning"
            except (KeyError, IndexError, TypeError) as exc:
                error = f"unexpected_response: {exc}"
        return LlmResponse(
            text,
            provider,
            config.model,
            raw,
            error,
            int((time.perf_counter() - started) * 1000),
        )

    if provider == "gemini":
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{config.model}:generateContent?key={config.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
            },
        }
        raw, error = _post(url, payload, {}, config.timeout_seconds)
        text = ""
        if raw:
            try:
                parts = raw["candidates"][0]["content"]["parts"]
                text = " ".join(part.get("text", "") for part in parts).strip()
            except (KeyError, IndexError, TypeError) as exc:
                error = f"unexpected_response: {exc}"
        return LlmResponse(
            text,
            provider,
            config.model,
            raw,
            error,
            int((time.perf_counter() - started) * 1000),
        )

    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        raw, error = _post(url, payload, headers, config.timeout_seconds)
        text = ""
        if raw:
            try:
                text = " ".join(
                    block.get("text", "")
                    for block in raw["content"]
                    if block.get("type") == "text"
                ).strip()
            except (KeyError, TypeError) as exc:
                error = f"unexpected_response: {exc}"
        return LlmResponse(
            text,
            provider,
            config.model,
            raw,
            error,
            int((time.perf_counter() - started) * 1000),
        )

    return LlmResponse(
        "",
        provider,
        config.model,
        None,
        f"unsupported_provider: {provider}",
        int((time.perf_counter() - started) * 1000),
    )
