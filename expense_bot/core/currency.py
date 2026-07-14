"""Currency symbol handling for global support."""

from __future__ import annotations

# Symbol -> ISO 4217 code. Covers the most common global currencies.
SYMBOL_TO_CODE: dict[str, str] = {
    "$": "USD",
    "₹": "INR",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₩": "KRW",
    "₽": "RUB",
    "R$": "BRL",
    "A$": "AUD",
    "C$": "CAD",
    "₺": "TRY",
    "฿": "THB",
    "₫": "VND",
    "₱": "PHP",
    "₦": "NGN",
    "﷼": "SAR",
}

CODE_TO_SYMBOL: dict[str, str] = {
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "KRW": "₩",
    "RUB": "₽",
    "BRL": "R$",
    "AUD": "A$",
    "CAD": "C$",
    "TRY": "₺",
    "THB": "฿",
    "VND": "₫",
    "PHP": "₱",
    "NGN": "₦",
    "SAR": "﷼",
}

# A permissive set of ISO codes we accept as explicit text (e.g. "35 USD").
KNOWN_CODES: frozenset[str] = frozenset(CODE_TO_SYMBOL) | {
    "CHF", "CNY", "SGD", "HKD", "NZD", "ZAR", "AED", "MXN", "SEK", "NOK",
    "DKK", "PLN", "IDR", "MYR", "PKR", "BDT", "LKR", "EGP", "KES",
}


def symbol_for(code: str) -> str:
    """Return a display symbol for an ISO code (falls back to the code)."""
    return CODE_TO_SYMBOL.get(code.upper(), code.upper())


def format_amount(amount: float, currency: str) -> str:
    """Human-friendly amount, e.g. ``₹250.00`` or ``35.00 CHF``."""
    symbol = CODE_TO_SYMBOL.get(currency.upper())
    if symbol:
        return f"{symbol}{amount:,.2f}"
    return f"{amount:,.2f} {currency.upper()}"
