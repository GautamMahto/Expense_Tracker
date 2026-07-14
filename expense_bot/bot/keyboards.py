"""Inline keyboard builders for the Telegram UI."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..core.categories import DEFAULT_CATEGORIES
from ..core.schemas import ExportFormat, PaymentMethod
from .states import (
    CB_CONFIRM,
    CB_DATE,
    CB_EXPORT,
    CB_MENU,
    CB_NOTES,
    CB_PAYMENT,
    CB_REPORT,
    CB_SETTINGS,
    cb,
)


def _grid(buttons: list[InlineKeyboardButton], columns: int) -> list[list[InlineKeyboardButton]]:
    return [buttons[i : i + columns] for i in range(0, len(buttons), columns)]


def main_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("➕ Add Expense", callback_data=cb(CB_MENU, "add"))],
        [
            InlineKeyboardButton("📊 Today", callback_data=cb(CB_MENU, "today")),
            InlineKeyboardButton("📅 Monthly", callback_data=cb(CB_MENU, "monthly")),
        ],
        [
            InlineKeyboardButton("📈 Statistics", callback_data=cb(CB_MENU, "stats")),
            InlineKeyboardButton("💰 Budget", callback_data=cb(CB_MENU, "budget")),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data=cb(CB_MENU, "settings")),
            InlineKeyboardButton("❓ Help", callback_data=cb(CB_MENU, "help")),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def category_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(c.label, callback_data=cb("cat", c.name))
        for c in DEFAULT_CATEGORIES
    ]
    return InlineKeyboardMarkup(_grid(buttons, 2))


def date_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Today", callback_data=cb(CB_DATE, "today")),
            InlineKeyboardButton("Yesterday", callback_data=cb(CB_DATE, "yesterday")),
        ],
        [InlineKeyboardButton("📆 Choose Date", callback_data=cb(CB_DATE, "choose"))],
    ]
    return InlineKeyboardMarkup(rows)


def payment_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(m.value, callback_data=cb(CB_PAYMENT, m.value))
        for m in PaymentMethod
    ]
    return InlineKeyboardMarkup(_grid(buttons, 2))


def notes_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏭ Skip", callback_data=cb(CB_NOTES, "skip"))]]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Add Another", callback_data=cb(CB_CONFIRM, "another")),
                InlineKeyboardButton("🏠 Main Menu", callback_data=cb(CB_CONFIRM, "menu")),
            ]
        ]
    )


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Main Menu", callback_data=cb(CB_MENU, "home"))]]
    )


def report_export_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f"⬇ {fmt.value}", callback_data=cb(CB_EXPORT, fmt.value))
        for fmt in ExportFormat
    ]
    rows = _grid(buttons, 3)
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data=cb(CB_MENU, "home"))])
    return InlineKeyboardMarkup(rows)


def reports_menu() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("📊 Today", callback_data=cb(CB_REPORT, "today")),
            InlineKeyboardButton("🗓 Weekly", callback_data=cb(CB_REPORT, "weekly")),
            InlineKeyboardButton("📅 Monthly", callback_data=cb(CB_REPORT, "monthly")),
        ],
        [InlineKeyboardButton("🏠 Main Menu", callback_data=cb(CB_MENU, "home"))],
    ]
    return InlineKeyboardMarkup(rows)


def budget_menu(has_budgets: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("➕ Add / update", callback_data=cb("budget", "set"))]]
    if has_budgets:
        rows.append(
            [InlineKeyboardButton("🗑 Remove a budget", callback_data=cb("budget", "remove"))]
        )
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data=cb(CB_MENU, "home"))])
    return InlineKeyboardMarkup(rows)


def settings_menu() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("💱 Currency", callback_data=cb(CB_SETTINGS, "currency")),
            InlineKeyboardButton("🌍 Timezone", callback_data=cb(CB_SETTINGS, "timezone")),
        ],
        [
            InlineKeyboardButton("💳 Payment", callback_data=cb(CB_SETTINGS, "payment")),
            InlineKeyboardButton("📤 Export", callback_data=cb(CB_SETTINGS, "export")),
        ],
        [InlineKeyboardButton("⏰ Reminder", callback_data=cb(CB_SETTINGS, "reminder"))],
        [InlineKeyboardButton("🏠 Main Menu", callback_data=cb(CB_MENU, "home"))],
    ]
    return InlineKeyboardMarkup(rows)
