"""Add-expense conversation (finite-state machine)."""

from __future__ import annotations

from datetime import date, timedelta

from dateutil import parser as date_parser
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ...core.parsing import ParseError, parse_amount
from ...core.schemas import ExpenseCreate
from ...services.expense_service import ExpenseService
from .. import formatting
from ..deps import user_session
from ..keyboards import (
    category_keyboard,
    confirm_keyboard,
    date_keyboard,
    main_menu,
    payment_keyboard,
)
from ..states import AddExpense, parse_cb

DRAFT = "expense_draft"


def _skip_keyboard(namespace: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏭ Skip", callback_data=f"{namespace}:skip")]]
    )


# --- Entry points -----------------------------------------------------------

async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[DRAFT] = {}
    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text("💵 How much did you spend?")
    else:
        await update.effective_message.reply_text("💵 How much did you spend?")
    return AddExpense.AMOUNT


# --- Step 1: amount ----------------------------------------------------------

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    async with user_session(update) as (_, user):
        default_currency = user.currency
    try:
        result = parse_amount(update.message.text, default_currency=default_currency)
    except ParseError as exc:
        await update.message.reply_text(
            f"⚠️ {exc}\nPlease send a positive amount, e.g. `250`, `₹450` or `35 USD`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return AddExpense.AMOUNT

    context.user_data[DRAFT].update(
        {"amount": result.amount, "currency": result.currency or default_currency}
    )
    await update.message.reply_text(
        "🗂 Which category?", reply_markup=category_keyboard()
    )
    return AddExpense.CATEGORY


# --- Step 2: category --------------------------------------------------------

async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, name = parse_cb(query.data)
    context.user_data[DRAFT]["category"] = name
    await query.answer()
    await query.edit_message_text(
        "🏪 Where did you spend it? (merchant)\nType a name or skip.",
        reply_markup=_skip_keyboard("merch"),
    )
    return AddExpense.MERCHANT


# --- Step 3: merchant --------------------------------------------------------

async def receive_merchant_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[DRAFT]["merchant"] = update.message.text.strip()
    await update.message.reply_text("🗓 When was this expense?", reply_markup=date_keyboard())
    return AddExpense.DATE


async def skip_merchant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    context.user_data[DRAFT]["merchant"] = None
    await query.answer()
    await query.edit_message_text("🗓 When was this expense?", reply_markup=date_keyboard())
    return AddExpense.DATE


# --- Step 4: date ------------------------------------------------------------

async def receive_date_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, choice = parse_cb(query.data)
    await query.answer()

    if choice == "today":
        context.user_data[DRAFT]["expense_date"] = date.today()
    elif choice == "yesterday":
        context.user_data[DRAFT]["expense_date"] = date.today() - timedelta(days=1)
    elif choice == "choose":
        await query.edit_message_text(
            "📆 Type the date (e.g. `2026-07-10` or `10 July 2026`).",
            parse_mode=ParseMode.MARKDOWN,
        )
        return AddExpense.CHOOSE_DATE

    await query.edit_message_text("💳 Payment method?", reply_markup=payment_keyboard())
    return AddExpense.PAYMENT


async def receive_typed_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        parsed = date_parser.parse(update.message.text, fuzzy=True, dayfirst=True).date()
    except (ValueError, OverflowError):
        await update.message.reply_text(
            "⚠️ I couldn't read that date. Try `2026-07-10`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return AddExpense.CHOOSE_DATE
    if parsed > date.today():
        await update.message.reply_text("⚠️ The date can't be in the future. Try again.")
        return AddExpense.CHOOSE_DATE

    context.user_data[DRAFT]["expense_date"] = parsed
    await update.message.reply_text("💳 Payment method?", reply_markup=payment_keyboard())
    return AddExpense.PAYMENT


# --- Step 5: payment ---------------------------------------------------------

async def receive_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, method = parse_cb(query.data)
    context.user_data[DRAFT]["payment_method"] = method
    await query.answer()
    await query.edit_message_text("📝 Any notes?", reply_markup=_skip_keyboard("note"))
    return AddExpense.NOTES


# --- Step 6: notes -> save ---------------------------------------------------

async def receive_notes_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[DRAFT]["notes"] = update.message.text.strip()
    return await _save_and_confirm(update, context)


async def skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[DRAFT]["notes"] = None
    await update.callback_query.answer()
    return await _save_and_confirm(update, context)


async def _save_and_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = context.user_data.get(DRAFT, {})
    payload = ExpenseCreate(
        amount=draft["amount"],
        currency=draft["currency"],
        category=draft["category"],
        merchant=draft.get("merchant"),
        expense_date=draft.get("expense_date") or date.today(),
        payment_method=draft.get("payment_method"),
        notes=draft.get("notes"),
    )

    async with user_session(update) as (session, user):
        result = await ExpenseService(session).create(user.id, payload)
        currency = user.currency

    text = formatting.expense_confirmation(result.expense)
    if result.budget_alert is not None:
        text += "\n\n" + formatting.budget_alert(result.budget_alert, currency)

    # Confirmation may arrive via a button (edit) or a text message (reply).
    if update.callback_query is not None:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_keyboard()
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_keyboard()
        )
    context.user_data.pop(DRAFT, None)
    return AddExpense.CONFIRM


# --- Step 7: confirm ---------------------------------------------------------

async def after_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, action = parse_cb(query.data)
    await query.answer()
    if action == "another":
        context.user_data[DRAFT] = {}
        await query.edit_message_text("💵 How much did you spend?")
        return AddExpense.AMOUNT
    await query.edit_message_text(
        "🏠 *Main Menu*", parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(DRAFT, None)
    await update.effective_message.reply_text(
        "❌ Cancelled.", reply_markup=main_menu()
    )
    return ConversationHandler.END


def build_conversation() -> ConversationHandler:
    text_only = filters.TEXT & ~filters.COMMAND
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add, pattern=r"^menu:add$")],
        states={
            AddExpense.AMOUNT: [MessageHandler(text_only, receive_amount)],
            AddExpense.CATEGORY: [CallbackQueryHandler(receive_category, pattern=r"^cat:")],
            AddExpense.MERCHANT: [
                CallbackQueryHandler(skip_merchant, pattern=r"^merch:skip$"),
                MessageHandler(text_only, receive_merchant_text),
            ],
            AddExpense.DATE: [CallbackQueryHandler(receive_date_choice, pattern=r"^date:")],
            AddExpense.CHOOSE_DATE: [MessageHandler(text_only, receive_typed_date)],
            AddExpense.PAYMENT: [CallbackQueryHandler(receive_payment, pattern=r"^pay:")],
            AddExpense.NOTES: [
                CallbackQueryHandler(skip_notes, pattern=r"^note:skip$"),
                MessageHandler(text_only, receive_notes_text),
            ],
            AddExpense.CONFIRM: [CallbackQueryHandler(after_confirm, pattern=r"^confirm:")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", cancel)],
        name="add_expense",
        persistent=False,
    )
