"""Conversation (FSM) state identifiers and callback-data constants."""

from __future__ import annotations

from enum import IntEnum, auto


class AddExpense(IntEnum):
    """States for the add-expense conversation handler."""

    AMOUNT = auto()
    CATEGORY = auto()
    MERCHANT = auto()
    DATE = auto()
    CHOOSE_DATE = auto()
    PAYMENT = auto()
    NOTES = auto()
    CONFIRM = auto()


class SetBudget(IntEnum):
    CATEGORY = auto()
    LIMIT = auto()


class Settings(IntEnum):
    AWAIT_VALUE = auto()


# --- Callback-data namespaces (prefix:payload) ---
CB_MENU = "menu"
CB_CATEGORY = "cat"
CB_DATE = "date"
CB_PAYMENT = "pay"
CB_NOTES = "note"
CB_CONFIRM = "confirm"
CB_BUDGET = "budget"
CB_SETTINGS = "set"
CB_REPORT = "report"
CB_EXPORT = "export"
CB_NLP = "nlp"


def cb(namespace: str, payload: str = "") -> str:
    return f"{namespace}:{payload}"


def parse_cb(data: str) -> tuple[str, str]:
    namespace, _, payload = data.partition(":")
    return namespace, payload
