"""/start, main menu, help and the top-level callback router."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from ..deps import user_session
from ..keyboards import back_to_menu, main_menu
from ..states import parse_cb
from . import budget as budget_handlers
from . import reports as report_handlers
from . import settings as settings_handlers
from . import statistics as stats_handlers

WELCOME = (
    "👋 *Welcome to Expense Tracker!*\n\n"
    "I help you record and analyse your spending right here in Telegram.\n"
    "You can tap a button below, or just type naturally, e.g.\n"
    "`Spent ₹450 at Starbucks today`.\n\n"
    "What would you like to do?"
)

HELP_TEXT = (
    "❓ *Help*\n\n"
    "*Add an expense*\n"
    "• Tap ➕ Add Expense and follow the steps, or\n"
    "• Type it naturally: `Spent 250 on lunch today`\n\n"
    "*Reports*\n"
    "• 📊 Today — today's expenses & total\n"
    "• 📅 Monthly — full monthly breakdown & export\n"
    "• 📈 Statistics — spending insights\n\n"
    "*Budget* — set monthly limits per category; I'll warn you when you exceed one.\n"
    "*Settings* — currency, timezone, default payment, reminders, export format.\n\n"
    "*Commands*\n"
    "/start — main menu\n"
    "/cancel — abort the current action\n"
    "/help — this message"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with user_session(update):
        pass  # ensures the user is registered
    await update.effective_message.reply_text(
        WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        HELP_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu()
    )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the main menu, editing the message when triggered by a button."""
    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text(
            WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
        )
    else:
        await update.effective_message.reply_text(
            WELCOME, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
        )


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatch top-level ``menu:<action>`` callbacks."""
    query = update.callback_query
    _, action = parse_cb(query.data)

    if action in {"home"}:
        await show_menu(update, context)
    elif action == "help":
        await query.answer()
        await query.edit_message_text(
            HELP_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu()
        )
    elif action == "today":
        await report_handlers.show_today(update, context)
    elif action == "monthly":
        await report_handlers.show_monthly(update, context)
    elif action == "stats":
        await stats_handlers.show_statistics(update, context)
    elif action == "budget":
        await budget_handlers.show_budget(update, context)
    elif action == "settings":
        await settings_handlers.show_settings(update, context)
    else:
        await query.answer("Unknown action")


def register(app) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(menu_router, pattern=r"^menu:"))
