"""Rule-based parsing of amounts, currencies and free-text expense messages.

This module is intentionally dependency-free and deterministic. The natural
language layer (:func:`parse_expense_text`) is the extension point where an
LLM-based extractor could be swapped in later without changing callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from dateutil import parser as date_parser

from .categories import guess_category
from .currency import KNOWN_CODES, SYMBOL_TO_CODE

# Number like 250, 1,250.50, 30.5. The comma-grouped form is tried first but
# must actually contain a comma group, otherwise a plain number (e.g. 1250.50)
# would be truncated to its first three digits.
_NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_SYMBOLS = "".join(re.escape(s) for s in SYMBOL_TO_CODE if len(s) == 1)

# Matches an optional currency symbol/code before or after a number.
_AMOUNT_RE = re.compile(
    rf"(?P<sym_before>[{_SYMBOLS}]|R\$|A\$|C\$)?\s*"
    rf"(?P<number>{_NUMBER})"
    rf"\s*(?P<code_after>[A-Za-z]{{3}})?",
)


class ParseError(ValueError):
    """Raised when an amount cannot be understood."""


@dataclass
class AmountResult:
    amount: float
    currency: str | None  # ISO code if detected, else None (use user default)


@dataclass
class ExpenseDraft:
    """Partially-extracted expense from free text; fields may be missing."""

    amount: float | None = None
    currency: str | None = None
    merchant: str | None = None
    category: str | None = None
    expense_date: date | None = None

    @property
    def missing_required(self) -> list[str]:
        missing: list[str] = []
        if self.amount is None:
            missing.append("amount")
        if self.category is None:
            missing.append("category")
        return missing


def _to_float(raw: str) -> float:
    return float(raw.replace(",", ""))


def parse_amount(text: str, *, default_currency: str | None = None) -> AmountResult:
    """Parse a standalone amount input such as ``250``, ``₹450`` or ``35 USD``.

    Raises :class:`ParseError` for non-numeric or negative inputs.
    """
    cleaned = text.strip()
    if cleaned.startswith("-"):
        raise ParseError("Amount cannot be negative.")

    match = _AMOUNT_RE.search(cleaned)
    if not match or not match.group("number"):
        raise ParseError("I couldn't find a valid amount.")

    amount = _to_float(match.group("number"))
    if amount <= 0:
        raise ParseError("Amount must be greater than zero.")

    currency: str | None = None
    sym = match.group("sym_before")
    code = match.group("code_after")
    if sym and sym in SYMBOL_TO_CODE:
        currency = SYMBOL_TO_CODE[sym]
    elif code and code.upper() in KNOWN_CODES:
        currency = code.upper()

    return AmountResult(amount=amount, currency=currency or default_currency)


def _extract_date(text: str) -> date | None:
    lowered = text.lower()
    today = date.today()
    if "today" in lowered:
        return today
    if "yesterday" in lowered:
        return today - timedelta(days=1)
    if "tomorrow" in lowered:
        return today + timedelta(days=1)
    # Try to find an explicit date fragment (e.g. "on 12 July", "2026-07-01").
    date_fragment = re.search(
        r"\bon\s+(.+?)(?:\.|$)|(\d{4}-\d{2}-\d{2})|(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        lowered,
    )
    if date_fragment:
        candidate = next((g for g in date_fragment.groups() if g), None)
        if candidate:
            try:
                return date_parser.parse(candidate, fuzzy=True, dayfirst=True).date()
            except (ValueError, OverflowError):
                return None
    return None


def _extract_merchant(text: str) -> str | None:
    # Grab the token(s) following "at" / "from", stopping at date words.
    match = re.search(
        r"\b(?:at|from|in)\s+([A-Za-z0-9'&.\- ]+?)"
        r"(?=\s+(?:today|yesterday|tomorrow|on|for)\b|[.,]|$)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        merchant = match.group(1).strip()
        return merchant or None
    return None


def parse_expense_text(text: str, *, default_currency: str | None = None) -> ExpenseDraft:
    """Extract as much structured expense data as possible from free text.

    Example: ``"Spent ₹450 at Starbucks today"`` yields amount=450,
    currency=INR, merchant="Starbucks", category="Food", date=today.
    """
    draft = ExpenseDraft(currency=default_currency)

    try:
        amount_result = parse_amount(text, default_currency=default_currency)
        draft.amount = amount_result.amount
        draft.currency = amount_result.currency
    except ParseError:
        pass

    draft.merchant = _extract_merchant(text)
    draft.expense_date = _extract_date(text)

    # Category: prefer merchant keywords, fall back to the full message.
    hint_source = draft.merchant or ""
    draft.category = guess_category(hint_source) or guess_category(text)

    return draft
