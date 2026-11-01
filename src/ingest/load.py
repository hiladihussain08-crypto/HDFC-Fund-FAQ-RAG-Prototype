"""Phase 2 (load): turn raw HTML into clean, chunk-ready documents.

Reads only ``artifacts/01_raw`` (no network).  For Groww scheme/AMC pages the
server-rendered ``__NEXT_DATA__`` payload is parsed into a canonical fact
dictionary.  Everything else goes through a readable-text extractor.

Output: ``artifacts/01_loaded/documents.jsonl`` + manifest + ``skipped.json``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.config import AppConfig, load_config
from src.utils import (
    clean_number,
    clean_text,
    format_inr,
    one_line,
    read_json,
    write_json,
    write_jsonl,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


NOISE_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "nav",
    "footer",
    "aside",
    "form",
    "iframe",
    "button",
)

NOISE_ATTR_RE = re.compile(
    r"(?i)(^|[-_ ])(nav|navbar|footer|menu|sidebar|cookie|consent|banner|promo|"
    r"social|breadcrumb|app[-_ ]?download|most[-_ ]?searched|related|"
    r"advertisement|popup)([-_ ]|$)"
)

BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "p", "li", "tr", "dt", "dd")

HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5")

# Lines that are navigation / boilerplate on Groww pages.
BOILERPLATE_RE = re.compile(
    r"(?i)^(home|login|register|download the app|contact us|about us|pricing|blog|"
    r"careers|help & support|trust & safety|investor relations|products|stocks|"
    r"f&o|mtf|etf|ipo|mutual funds|commodities|demat account|groww amc|pms|bonds|"
    r"terms and conditions|privacy policy|disclosure|download forms|"
    r"was the answer helpful\??|arrow indicating more options|show more)$"
)


STRUCTURAL_TAGS = {"html", "body", "main", "article"}


def _is_noise(tag: Tag) -> bool:
    # Never decompose page containers: a single matching class on <body>
    # (e.g. "page-header-menu-fixed") would otherwise delete the whole page.
    if tag.name in STRUCTURAL_TAGS:
        return False
    if tag.name in NOISE_TAGS:
        return True
    raw_attrs = getattr(tag, "attrs", None) or {}
    attrs = " ".join(
        str(value)
        for key, value in raw_attrs.items()
        if key in {"class", "id", "role", "aria-label"}
    )
    if not attrs or not NOISE_ATTR_RE.search(attrs):
        return False
    # Keep large content wrappers even if their class looks navigational.
    return len(tag.get_text(" ", strip=True)) < 1200


def _remove_noise(soup: BeautifulSoup) -> None:
    # Materialise the list first: decompose() detaches nodes mid-iteration and
    # detached tags no longer carry usable attrs.
    for tag in list(soup.find_all(True)):
        if _is_noise(tag):
            tag.decompose()


def _choose_root(soup: BeautifulSoup) -> Tag:
    for selector in ("main", "[role=main]", "article"):
        node = soup.select_one(selector)
        if node and len(node.get_text(" ", strip=True)) > 400:
            return node
    return soup.body or soup


def _extract_sections_from_root(
    root: Tag, fallback_heading: str
) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    heading = fallback_heading
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = clean_text("\n".join(buffer))
        if text:
            sections.append({"heading": heading, "text": text})
        buffer = []

    for element in root.find_all(BLOCK_TAGS):
        if element.find_parent(BLOCK_TAGS[:-1]) and element.name not in {"tr"}:
            # Nested paragraph/list nodes are captured through their parent.
            if element.name not in HEADING_TAGS:
                continue
        if element.name in HEADING_TAGS:
            text = one_line(element.get_text(" "))
            if text:
                flush()
                heading = text
            continue
        if element.name == "tr":
            cells = [
                one_line(cell.get_text(" "))
                for cell in element.find_all(["td", "th"])
            ]
            cells = [cell for cell in cells if cell]
            if not cells:
                continue
            line = cells[0] if len(cells) == 1 else f"{cells[0]}: " + " | ".join(cells[1:])
        else:
            line = one_line(element.get_text(" "))
        if not line or BOILERPLATE_RE.match(line):
            continue
        if len(line) < 3:
            continue
        buffer.append(line)

    flush()

    # Drop exact duplicates while preserving order.
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for section in sections:
        key = f"{section['heading']}::{section['text']}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(section)
    return unique


def extract_sections(soup: BeautifulSoup, fallback_heading: str) -> list[dict[str, str]]:
    """Split readable HTML into heading-scoped sections.

    Tables become ``key: value | value`` lines so fact rows survive chunking.
    If the chosen ``<main>`` yields almost nothing (portals that render body
    content outside ``<main>``), retry on ``<body>``.
    """

    root = _choose_root(soup)
    sections = _extract_sections_from_root(root, fallback_heading)
    total = sum(len(section["text"]) for section in sections)
    body = soup.body
    if total < 80 and body is not None and body is not root:
        fallback = _extract_sections_from_root(body, fallback_heading)
        if sum(len(section["text"]) for section in fallback) > total:
            sections = fallback
    return sections


def _next_data(soup: BeautifulSoup) -> dict[str, Any] | None:
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return None
    try:
        return json.loads(script.string)
    except json.JSONDecodeError:
        return None


def _fmt_percent(value: Any) -> str:
    """Keep source precision (1.20%, 0.75%) instead of collapsing to 1.2%."""
    if value is None or value == "":
        return ""
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        text = one_line(str(value))
        return text if text.endswith("%") else f"{text}%"


def _fmt_amount(value: Any) -> str:
    if value is None:
        return ""
    try:
        return format_inr(float(value))
    except (TypeError, ValueError):
        return one_line(str(value))


def _fmt_lock_in(lock_in: dict[str, Any] | None) -> str:
    if not lock_in:
        return "No lock-in"
    parts: list[str] = []
    for unit in ("years", "months", "days"):
        value = lock_in.get(unit)
        if value:
            label = unit[:-1] if value == 1 else unit
            parts.append(f"{clean_number(value)} {label}")
    return " ".join(parts) if parts else "No lock-in"


def _fmt_risk(value: Any) -> str:
    text = one_line(str(value or ""))
    return re.sub(r"(?i)\s*riskometer$", "", text).strip()


def _scheme_facts(payload: dict[str, Any]) -> dict[str, str]:
    category = one_line(str(payload.get("category") or ""))
    sub_category = one_line(str(payload.get("sub_category") or ""))
    category_text = " - ".join(part for part in (category, sub_category) if part)
    plan = " ".join(
        part
        for part in (
            one_line(str(payload.get("plan_type") or "")),
            one_line(str(payload.get("scheme_type") or "")),
        )
        if part
    )
    benchmark = one_line(str(payload.get("benchmark") or ""))
    benchmark_name = one_line(str(payload.get("benchmark_name") or ""))
    benchmark_text = (
        f"{benchmark} ({benchmark_name})"
        if benchmark and benchmark_name and benchmark.lower() not in benchmark_name.lower()
        else benchmark or benchmark_name
    )

    facts = {
        "scheme_name": one_line(str(payload.get("scheme_name") or "")),
        "fund_house": one_line(str(payload.get("fund_house") or "")),
        "category": category_text,
        "plan": plan,
        "expense_ratio": _fmt_percent(payload.get("expense_ratio")),
        "base_expense_ratio": _fmt_percent(payload.get("base_expense_ratio")),
        "exit_load": one_line(str(payload.get("exit_load") or "")),
        "min_sip": _fmt_amount(payload.get("min_sip_investment")),
        "min_lumpsum": _fmt_amount(payload.get("min_investment_amount")),
        "min_additional": _fmt_amount(payload.get("mini_additional_investment")),
        "lock_in": _fmt_lock_in(payload.get("lock_in")),
        "riskometer": _fmt_risk(payload.get("nfo_risk")),
        "benchmark": benchmark_text,
        "aum": f"{_fmt_amount(payload.get('aum'))} crore"
        if payload.get("aum") is not None and _fmt_amount(payload.get("aum"))
        else "",
        "fund_manager": one_line(str(payload.get("fund_manager") or "")),
        "launch_date": one_line(str(payload.get("launch_date") or "")),
        "stamp_duty": one_line(str(payload.get("stamp_duty") or "")),
        "description": one_line(str(payload.get("description") or "")),
    }
    return {key: value for key, value in facts.items() if value}


def _amc_facts(payload: dict[str, Any]) -> dict[str, str]:
    facts: dict[str, str] = {}
    key_information = payload.get("key_information") or {}
    for key, value in key_information.items():
        if value is None or isinstance(value, (dict, list)):
            continue
        text = one_line(str(value))
        if not text:
            continue
        label = key.replace("_", " ").strip().capitalize()
        facts[label] = text
    return facts


def _structured_sections(payload: dict[str, Any]) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    content_list = payload.get("contentList") or []
    for item in content_list:
        if not isinstance(item, dict):
            continue
        title = one_line(str(item.get("title") or ""))
        html = item.get("content") or ""
        text = one_line(BeautifulSoup(str(html), "lxml").get_text(" "))
        if text:
            sections.append({"heading": title or "About", "text": text})
    return sections


def _parse_groww(
    soup: BeautifulSoup,
) -> tuple[dict[str, str], list[dict[str, str]], str]:
    """Return (facts, structured_sections, kind) for Groww pages."""

    data = _next_data(soup)
    if not data:
        return {}, [], ""
    page_props = (data.get("props") or {}).get("pageProps") or {}

    scheme_payload = page_props.get("mfServerSideData")
    if isinstance(scheme_payload, dict) and scheme_payload.get("scheme_name"):
        return _scheme_facts(scheme_payload), [], "groww_next_data:scheme"

    amc_payload = page_props.get("amcMainPageData")
    if isinstance(amc_payload, list):
        for item in amc_payload:
            if isinstance(item, dict) and item.get("key_information"):
                return (
                    _amc_facts(item),
                    _structured_sections(item),
                    "groww_next_data:amc",
                )
    return {}, [], ""


def _read_meta(raw_dir: Path, page_id: str) -> dict[str, Any]:
    path = raw_dir / f"{page_id}.json"
    return read_json(path) if path.exists() else {}


def load_documents(config: AppConfig | None = None) -> list[dict[str, Any]]:
    config = config or load_config()
    config.ensure_dirs()
    raw_dir = config.raw_dir
    loaded_dir = config.loaded_dir

    html_files = sorted(raw_dir.glob("*.html"))
    if not html_files:
        raise FileNotFoundError(
            f"No scraped HTML in {raw_dir}. Run phase 2 (scrape) first."
        )

    documents: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for html_path in html_files:
        page_id = html_path.stem
        meta = _read_meta(raw_dir, page_id)
        status = int(meta.get("http_status") or 0)
        if status != 200:
            skipped.append(
                {
                    "id": page_id,
                    "reason": f"http_status={status}",
                    "error": meta.get("error"),
                }
            )
            continue

        raw_bytes = html_path.read_bytes()
        if not raw_bytes:
            skipped.append({"id": page_id, "reason": "empty html"})
            continue

        soup = BeautifulSoup(raw_bytes, "lxml")
        title = (
            one_line(soup.title.get_text(" ")) if soup.title else meta.get("title", "")
        )
        soup_title = re.sub(r"\s*\|\s*Groww\s*$", "", title).strip()

        facts, extra_sections, extraction = _parse_groww(soup)
        _remove_noise(soup)
        sections = extract_sections(soup, soup_title or page_id)
        sections.extend(extra_sections)

        text = clean_text(
            "\n".join(
                f"{section['heading']}\n{section['text']}" for section in sections
            )
        )
        if not text and facts:
            text = "\n".join(f"{key}: {value}" for key, value in facts.items())

        if len(text) < 80 and not facts:
            skipped.append(
                {
                    "id": page_id,
                    "reason": "empty extract",
                    "text_chars": len(text),
                }
            )
            continue

        document = {
            "id": page_id,
            "url": meta.get("url", ""),
            "title": soup_title or meta.get("title", page_id),
            "category": meta.get("category", ""),
            "scheme": meta.get("scheme", ""),
            "doc_type": meta.get("doc_type", ""),
            "fetched_at": meta.get("fetched_at", ""),
            "http_status": status,
            "extraction": extraction or "html_text",
            "text": text,
            "sections": sections,
            "facts": facts,
            "char_count": len(text),
            "word_count": len(text.split()),
        }
        documents.append(document)
        print(
            f"ok   {page_id:<32} {len(text):>7} chars  "
            f"{len(sections):>3} sections  {len(facts):>2} facts  "
            f"[{document['extraction']}]"
        )

    write_jsonl(loaded_dir / "documents.jsonl", documents)
    write_json(loaded_dir / "skipped.json", skipped)
    manifest = {
        "phase": "01_loaded",
        "loaded": len(documents),
        "skipped": len(skipped),
        "documents": [
            {
                "id": doc["id"],
                "chars": doc["char_count"],
                "sections": len(doc["sections"]),
                "facts": len(doc["facts"]),
                "extraction": doc["extraction"],
            }
            for doc in documents
        ],
        "skipped_ids": [item["id"] for item in skipped],
    }
    write_json(loaded_dir / "manifest.json", manifest)
    print(f"\nLoaded {len(documents)} documents, skipped {len(skipped)}.")
    return documents


def main() -> None:
    load_documents()


if __name__ == "__main__":
    main()
