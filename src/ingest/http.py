"""HTTP helper shared by the scraper.

Uses httpx with browser-like headers, retries, and a TLS-verification fallback
for public sites whose certificate chain is incomplete on some Windows setups.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Cache-Control": "no-cache",
}


@dataclass
class FetchResult:
    status: int
    body: bytes
    error: str | None
    final_url: str
    tls_verified: bool


def fetch(url: str, timeout: int = 40, retries: int = 1) -> FetchResult:
    last_error: str | None = None
    attempts = retries + 1

    for attempt in range(attempts):
        try:
            with httpx.Client(
                headers=HEADERS,
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                response = client.get(url)
                return FetchResult(
                    status=response.status_code,
                    body=response.content,
                    error=None if response.status_code < 400 else response.reason_phrase,
                    final_url=str(response.url),
                    tls_verified=True,
                )
        except httpx.HTTPError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            message = str(exc).lower()
            if "certificate" in message or "ssl" in message:
                try:
                    with httpx.Client(
                        headers=HEADERS,
                        timeout=timeout,
                        follow_redirects=True,
                        verify=False,
                    ) as client:
                        response = client.get(url)
                        return FetchResult(
                            status=response.status_code,
                            body=response.content,
                            error=None
                            if response.status_code < 400
                            else response.reason_phrase,
                            final_url=str(response.url),
                            tls_verified=False,
                        )
                except httpx.HTTPError as inner:
                    last_error = f"{type(inner).__name__}: {inner}"
            if attempt < attempts - 1:
                time.sleep(1.0 + attempt)

    return FetchResult(
        status=0,
        body=b"",
        error=last_error or "unknown fetch error",
        final_url=url,
        tls_verified=True,
    )
