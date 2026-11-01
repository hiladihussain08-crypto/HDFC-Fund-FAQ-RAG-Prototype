"""W1 guard: decide answer vs refuse vs miss *before* retrieval.

Routes
------
answer          factual, in-scope question -> retrieval + generation
refuse_advice   buy/sell/hold/portfolio/ranking -> fixed refusal + education link
refuse_returns  return/NAV/performance math    -> fixed refusal + education link
refuse_pii      PAN/Aadhaar/OTP/email/phone... -> fixed refusal, never persisted
miss            unknown fund, ambiguous scheme, empty/gibberish -> honest miss
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.config import AppConfig
from src.schemes import (
    SCHEMES,
    Scheme,
    covered_scheme_list,
    detect_scheme,
    is_statement_question,
    mentions_foreign_amc,
    mentions_hdfc,
    mentions_uncovered_hdfc_scheme,
)

ANSWER = "answer"
REFUSE_ADVICE = "refuse_advice"
REFUSE_RETURNS = "refuse_returns"
REFUSE_PII = "refuse_pii"
MISS = "miss"

PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)),
    (
        "Aadhaar",
        re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"),
    ),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    (
        "phone",
        re.compile(
            r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
        ),
    ),
    ("OTP", re.compile(r"\b(?:otp|one[\s-]?time\s+password)\b", re.IGNORECASE)),
    (
        "account number",
        re.compile(
            r"\b(?:a/c|acct|account)\s*(?:no\.?|number|#)?\s*[:=-]?\s*\d{6,18}\b",
            re.IGNORECASE,
        ),
    ),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)),
    ("UPI ID", re.compile(r"\b[\w.\-]+@(?:oksbi|okhdfcbank|okicici|okaxis|paytm|ybl|upi)\b", re.IGNORECASE)),
    ("card number", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
)

ADVICE_RE = re.compile(
    r"\b(should i|should we|shall i|is it (a )?good|worth (investing|buying)|"
    r"buy|sell|hold|invest in|investment advice|portfolio|recommend|"
    r"suggestion|best|better|which (fund|scheme|one)|allocate|allocation|"
    r"switch|stop( my)? sip|start( a)? sip|exit now|book profit|"
    r"good time|market timing|safe (fund|option)|suitable for me|"
    r"risk profile|multiply|double my)\b",
    re.IGNORECASE,
)

RETURNS_RE = re.compile(
    r"\b(returns?|cagr|xirr|annuali[sz]ed|performance|perform(?:ed|ing)?|profit|"
    r"loss|gains?|nav|alpha|beta|sharpe|sortino|outperform|underperform|compare|"
    r"comparison|beat the market|since inception|last year|past year)\b",
    re.IGNORECASE,
)

GREETING_RE = re.compile(
    r"^\s*(hi|hello|hey|good (morning|afternoon|evening)|namaste|thanks|thank you)\s*[!.?]*\s*$",
    re.IGNORECASE,
)

INTENTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("expense_ratio", re.compile(r"\b(expense|expence|ter|total expense)\b", re.I)),
    ("exit_load", re.compile(r"\b(exit load|exit-load|redemption charge)\b", re.I)),
    ("min_sip", re.compile(r"\b(minimum|min)\s*(sip|systematic)|sip amount\b", re.I)),
    (
        "min_investment",
        re.compile(r"\b(minimum|min)\s*(lump\s?sum|investment)\b", re.I),
    ),
    ("lock_in", re.compile(r"\block[\s-]?in\b", re.I)),
    ("riskometer", re.compile(r"\brisk[\s-]?o[\s-]?meter|\brisk level\b", re.I)),
    ("benchmark", re.compile(r"\bbenchmark|index tracked\b", re.I)),
    ("fund_manager", re.compile(r"\bfund manager|who manages\b", re.I)),
    (
        "fund_house",
        re.compile(r"\bfund house\b|\bamc\b|asset management company", re.I),
    ),
    ("aum", re.compile(r"\baum\b|asset under management|assets under management", re.I)),
    ("category", re.compile(r"\bcategory\b|\btype of fund\b", re.I)),
    ("launch_date", re.compile(r"\blaunch(ed)?\b|\binception\b", re.I)),
    ("stamp_duty", re.compile(r"\bstamp duty\b", re.I)),
    ("statement", re.compile(r"\bstatement|capital gain|80c|tax proof|cas\b", re.I)),
)


@dataclass
class GuardResult:
    route: str
    reason: str
    log_question: str
    question: str
    scheme: Scheme | None = None
    statement: bool = False
    intent: str = "other"
    message: str = ""
    citation_source_id: str = ""
    pii_types: tuple[str, ...] = field(default_factory=tuple)

    @property
    def needs_retrieval(self) -> bool:
        return self.route == ANSWER


def detect_intent(question: str) -> str:
    for name, pattern in INTENTS:
        if pattern.search(question):
            return name
    return "other"


def detect_pii(question: str) -> tuple[str, ...]:
    found: list[str] = []
    for label, pattern in PII_PATTERNS:
        if pattern.search(question):
            found.append(label)
    return tuple(dict.fromkeys(found))


def detect_advice(question: str) -> bool:
    return bool(ADVICE_RE.search(question))


def detect_returns(question: str) -> bool:
    if is_statement_question(question):
        # "capital gains statement", "P&L statement" are document requests,
        # not performance calculations.
        return False
    return bool(RETURNS_RE.search(question))


def _scheme_count(question: str) -> int:
    lowered = question.lower()
    hits = 0
    for scheme in SCHEMES:
        if any(
            re.search(rf"\b{re.escape(alias)}\b", lowered)
            for alias in scheme.aliases
        ):
            hits += 1
    return hits


def _miss(
    question: str,
    reason: str,
    message: str,
    citation_source_id: str = "groww-amc-hdfc",
    scheme: Scheme | None = None,
    statement: bool = False,
) -> GuardResult:
    return GuardResult(
        route=MISS,
        reason=reason,
        log_question=question,
        question=question,
        scheme=scheme,
        statement=statement,
        intent=detect_intent(question),
        message=message,
        citation_source_id=citation_source_id,
    )


def guard_question(question: str, config: AppConfig | None = None) -> GuardResult:
    question = (question or "").strip()
    scheme = detect_scheme(question)
    statement = is_statement_question(question)
    intent = detect_intent(question)
    covered = covered_scheme_list()

    # 1. PII always wins: refuse and never persist the raw text.
    pii_types = detect_pii(question)
    if pii_types:
        return GuardResult(
            route=REFUSE_PII,
            reason="pii:" + ",".join(pii_types),
            log_question="[redacted: PII detected]",
            question=question,
            scheme=scheme,
            statement=statement,
            intent=intent,
            message=(
                "I can't accept or store PAN, Aadhaar, account numbers, OTPs, "
                "emails, or phone numbers. Please remove that information and ask "
                "a factual question about a covered HDFC scheme."
            ),
            citation_source_id="sebi-secure-account",
            pii_types=pii_types,
        )

    if not question or GREETING_RE.match(question):
        return _miss(
            question or "",
            "empty_or_greeting",
            "Please ask a factual question about one of the covered HDFC schemes, "
            "for example: What is the minimum SIP for HDFC Mid Cap Fund Direct Growth?",
        )

    normalised = re.sub(r"[^A-Za-z0-9\s]", "", question).strip()
    if len(normalised) < 3 or not re.search(r"[A-Za-z]", normalised):
        return _miss(
            question,
            "gibberish",
            "Please ask a specific factual question about one of the covered HDFC "
            "schemes, for example: What is the expense ratio of HDFC Large Cap Fund "
            "Direct Growth?",
        )

    # 2. Advice / opinion / ranking.
    if detect_advice(question):
        return GuardResult(
            route=REFUSE_ADVICE,
            reason="advice_or_ranking",
            log_question=question,
            question=question,
            scheme=scheme,
            statement=statement,
            intent=intent,
            message=(
                "I can only share factual information about the schemes covered "
                "here, so I can't recommend whether to buy, sell, or hold. For "
                "general investor education, see the SEBI Investor Education page."
            ),
            citation_source_id="sebi-investor-home",
        )

    # 3. Returns / NAV / performance math.
    if detect_returns(question):
        return GuardResult(
            route=REFUSE_RETURNS,
            reason="returns_or_performance",
            log_question=question,
            question=question,
            scheme=scheme,
            statement=statement,
            intent=intent,
            message=(
                "I don't compute or compare returns, NAV movements, or fund "
                "performance. For investor education on risk and returns, see the "
                "SEBI Investor Education page."
            ),
            citation_source_id="sebi-personal-investments",
        )

    # 4. Out-of-corpus AMC / fund.
    if mentions_foreign_amc(question) and not mentions_hdfc(question):
        return _miss(
            question,
            "foreign_amc",
            f"That scheme isn't in the pages I loaded. I cover these HDFC schemes: {covered}.",
        )

    if mentions_uncovered_hdfc_scheme(question) and scheme is None:
        return _miss(
            question,
            "uncovered_hdfc_scheme",
            f"That HDFC scheme isn't in the pages I loaded. I cover: {covered}.",
        )

    if _scheme_count(question) > 1:
        return _miss(
            question,
            "multiple_schemes",
            f"Please ask about one scheme at a time. I cover: {covered}.",
        )

    # 5. Need a scheme for scheme-specific facts; statement questions are the
    #    only generic intent supported by the corpus.
    if scheme is None and not statement:
        return _miss(
            question,
            "missing_scheme",
            f"Please name one of the covered HDFC schemes so I can look up the "
            f"exact fact: {covered}.",
        )

    return GuardResult(
        route=ANSWER,
        reason="factual",
        log_question=question,
        question=question,
        scheme=scheme,
        statement=statement and scheme is None,
        intent=intent,
        citation_source_id="",
    )
