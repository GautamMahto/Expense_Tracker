"""Unit tests for amount / currency / natural-language parsing."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from expense_bot.core.currency import format_amount
from expense_bot.core.parsing import ParseError, parse_amount, parse_expense_text


@pytest.mark.parametrize(
    ("text", "amount", "currency"),
    [
        ("250", 250.0, None),
        ("1250.50", 1250.50, None),
        ("35 USD", 35.0, "USD"),
        ("₹450", 450.0, "INR"),
        ("€30", 30.0, "EUR"),
        ("1,250.50", 1250.50, None),
    ],
)
def test_parse_amount_valid(text, amount, currency):
    result = parse_amount(text)
    assert result.amount == amount
    assert result.currency == currency


@pytest.mark.parametrize("text", ["-5", "abc", "", "  ", "0"])
def test_parse_amount_invalid(text):
    with pytest.raises(ParseError):
        parse_amount(text)


def test_parse_amount_uses_default_currency():
    result = parse_amount("100", default_currency="GBP")
    assert result.currency == "GBP"


def test_parse_expense_text_full():
    draft = parse_expense_text("Spent ₹450 at Starbucks today")
    assert draft.amount == 450.0
    assert draft.currency == "INR"
    assert draft.merchant == "Starbucks"
    assert draft.category == "Food"
    assert draft.expense_date == date.today()


def test_parse_expense_text_yesterday_and_merchant():
    draft = parse_expense_text("Paid 20 at Uber yesterday")
    assert draft.amount == 20.0
    assert draft.merchant == "Uber"
    assert draft.category == "Transport"
    assert draft.expense_date == date.today() - timedelta(days=1)


def test_parse_expense_text_missing_category():
    draft = parse_expense_text("Spent 500")
    assert draft.amount == 500.0
    assert "category" in draft.missing_required


def test_format_amount():
    assert format_amount(250, "INR") == "₹250.00"
    assert format_amount(35, "CHF") == "35.00 CHF"
