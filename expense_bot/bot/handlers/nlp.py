"""Natural-language expense logging (free-text entry).

Parses messages like ``Spent ₹450 at Starbucks today`` and only asks for
fields that could not be extracted (per the spec). Implemented as its own
conversation so a missing category can be collected without losing context.
"""

from __future__ import annotations

from datetime import date
from enum import IntEnum, auto

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ...core.parsing import parse_expense_text
from ...core.schemas import ExpenseCreate
from ...services.expense_service import ExpenseService
from .. import formatting
from ..deps import user_session
from ..keyboards import category_keyboard, main_menu
from ..states import parse_cb

NLP_DRAFT = "nlp_draft"


class NlpState(IntEnum):
    CATEGORY = auto()


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    async with user_session(update) as (_, user):
        default_currency = user.currency
    draft = parse_expense_text(text, default_currency=default_currency)

    if draft.amount is None:
        await update.message.reply_text(
            "🤔 I couldn't find an amount. Try `Spent 250 on lunch today`, "
            "or use the menu.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    context.user_data[NLP_DRAFT] = {
        "amount": draft.amount,
        "currency": draft.currency or default_currency,
        "merchant": draft.merchant,
        "expense_date": draft.expense_date or date.today(),
    }

    if draft.category is None:
        await update.message.reply_text(
            "Which category should I assign?", reply_markup=category_keyboard()
        )
        return NlpState.CATEGORY

    context.user_data[NLP_DRAFT]["category"] = draft.category
    return await _finalise(update, context)


async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, name = parse_cb(query.data)
    context.user_data[NLP_DRAFT]["category"] = name
    await query.answer()
    return await _finalise(update, context)


async def _finalise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = context.user_data.pop(NLP_DRAFT)
    payload = ExpenseCreate(
        amount=draft["amount"],
        currency=draft["currency"],
        category=draft["category"],
        merchant=draft.get("merchant"),
        expense_date=draft["expense_date"],
        payment_method=None,
        notes=None,
    )
    async with user_session(update) as (session, user):
        result = await ExpenseService(session).create(user.id, payload)
        currency = user.currency

    text = formatting.expense_confirmation(result.expense)
    if result.budget_alert is not None:
        text += "\n\n" + formatting.budget_alert(result.budget_alert, currency)

    query = update.callback_query
    if query is not None:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
        )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(NLP_DRAFT, None)
    await update.effective_message.reply_text("❌ Cancelled.", reply_markup=main_menu())
    return ConversationHandler.END


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
        ],
        states={
            NlpState.CATEGORY: [CallbackQueryHandler(receive_category, pattern=r"^cat:")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", cancel)],
        name="nlp_entry",
        persistent=False,
    )
