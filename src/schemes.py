"""Canonical scheme registry and question-level scheme detection.

This is the W1 layer that decides *which fund* a question is about before
retrieval.  It prevents a question about an uncovered fund (e.g. SBI Bluechip)
from being answered with a similar HDFC chunk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Scheme:
    source_id: str
    name: str
    short_name: str
    aliases: tuple[str, ...]


SCHEMES: tuple[Scheme, ...] = (
    Scheme(
        source_id="groww-large-cap",
        name="HDFC Large Cap Fund Direct Growth",
        short_name="HDFC Large Cap Fund",
        aliases=("hdfc large cap", "large cap fund", "large-cap fund", "large cap", "top 200"),
    ),
    Scheme(
        source_id="groww-flexi-cap",
        name="HDFC Flexi Cap Direct Plan Growth",
        short_name="HDFC Flexi Cap Fund",
        aliases=(
            "hdfc flexi cap",
            "flexi cap",
            "flexicap",
            "hdfc equity fund",
            "equity fund direct",
        ),
    ),
    Scheme(
        source_id="groww-elss",
        name="HDFC ELSS Tax Saver Fund Direct Plan Growth",
        short_name="HDFC ELSS Tax Saver Fund",
        aliases=(
            "hdfc elss",
            "elss tax saver",
            "tax saver",
            "tax saving fund",
            "elss",
        ),
    ),
    Scheme(
        source_id="groww-mid-cap",
        name="HDFC Mid Cap Fund Direct Growth",
        short_name="HDFC Mid Cap Fund",
        aliases=("hdfc mid cap", "mid cap fund", "mid-cap fund", "mid cap", "midcap"),
    ),
)

SCHEME_BY_ID = {scheme.source_id: scheme for scheme in SCHEMES}

# Other AMCs / widely known non-covered funds.  A question about these never
# gets an HDFC answer.
_FOREIGN_AMC_RE = re.compile(
    r"\b(sbi|icici|axis|nippon|kotak|dsp|mirae|parag parikh|ppfas|quant|tata|"
    r"franklin|aditya birla|absl|uti|canara robeco|hsbc|bandhan|motilal oswal|"
    r"invesco|edelweiss|navi|pgim|sundaram|lic mf|baroda bnp|bajaj finserv|"
    r"whiteoak|jm financial|360 one|mahindra manulife|samco|trust mf|groww mutual fund)\b",
    re.IGNORECASE,
)

_UNCOVERED_HDFC_RE = re.compile(
    r"\b(small cap|balanced advantage|multi cap|multicap|index fund|nifty|sensex|"
    r"gold|silver|liquid|overnight|hybrid|arbitrage|contra|value fund|"
    r"dividend yield|infrastructure|banking|pharma|technology|focused|"
    r"children|retirement|savings|credit risk|corporate bond|gilt|money market)\b",
    re.IGNORECASE,
)

_STATEMENT_RE = re.compile(
    r"\b(statement|capital[- ]?gain|capital[- ]?gains|tax proof|80c|80 c|"
    r"consolidated account|cas|p&l|pnl|profit.?loss report|download report|"
    r"tax certificate)\b",
    re.IGNORECASE,
)


def detect_scheme(question: str) -> Scheme | None:
    """Return the single covered scheme explicitly named in the question."""

    lowered = question.lower()
    best: tuple[int, Scheme] | None = None
    for scheme in SCHEMES:
        for alias in scheme.aliases:
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                if best is None or len(alias) > best[0]:
                    best = (len(alias), scheme)
    return best[1] if best else None


def mentions_foreign_amc(question: str) -> bool:
    return bool(_FOREIGN_AMC_RE.search(question))


def mentions_hdfc(question: str) -> bool:
    return bool(re.search(r"\bhdfc\b", question, re.IGNORECASE))


def mentions_uncovered_hdfc_scheme(question: str) -> bool:
    return mentions_hdfc(question) and bool(_UNCOVERED_HDFC_RE.search(question))


def is_statement_question(question: str) -> bool:
    return bool(_STATEMENT_RE.search(question))


def covered_scheme_list() -> str:
    return ", ".join(scheme.short_name for scheme in SCHEMES)


def describe_schemes() -> list[dict[str, str]]:
    return [
        {"source_id": s.source_id, "name": s.name, "short_name": s.short_name}
        for s in SCHEMES
    ]
