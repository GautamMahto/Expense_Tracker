"""Budget viewing and configuration."""

from __future__ import annotations

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

from ...core.categories import DEFAULT_CATEGORIES
from ...core.currency import format_amount
from ...core.parsing import ParseError, parse_amount
from ...services.budget_service import BudgetService
from ..deps import user_session
from ..keyboards import budget_menu, main_menu
from ..states import SetBudget, parse_cb

BUDGET_CATEGORY = "budget_category"


def _budget_category_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(c.label, callback_data=f"bcat:{c.name}")
        for c in DEFAULT_CATEGORIES
        if c.name != "Other"
    ]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


async def show_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with user_session(update) as (session, user):
        statuses = await BudgetService(session).all_statuses(user.id)
        currency = user.currency

    if statuses:
        lines = ["💰 *Your Budgets*", ""]
        for s in statuses:
            pct = round(s.utilisation * 100)
            flag = " ⚠️" if s.exceeded else ""
            lines.append(
                f"• {s.category}: {format_amount(s.spent, currency)} / "
                f"{format_amount(s.monthly_limit, currency)} ({pct}%){flag}"
            )
        text = "\n".join(lines)
    else:
        text = "💰 *Budgets*\n\nNo budgets set yet. Add one to track your limits."

    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=budget_menu(bool(statuses))
        )
    else:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=budget_menu(bool(statuses))
        )


# --- Set-budget conversation ------------------------------------------------

async def start_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💰 Choose a category to budget:", reply_markup=_budget_category_keyboard()
    )
    return SetBudget.CATEGORY


async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, name = parse_cb(query.data)
    context.user_data[BUDGET_CATEGORY] = name
    await query.answer()
    await query.edit_message_text(
        f"What is the monthly limit for *{name}*?\nSend an amount, e.g. `5000`.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return SetBudget.LIMIT


async def receive_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        result = parse_amount(update.message.text)
    except ParseError as exc:
        await update.message.reply_text(f"⚠️ {exc} Try again, e.g. `5000`.")
        return SetBudget.LIMIT

    category = context.user_data.pop(BUDGET_CATEGORY, "Other")
    async with user_session(update) as (session, user):
        await BudgetService(session).set_budget(user.id, category, result.amount)
        currency = user.currency

    await update.message.reply_text(
        f"✅ Budget for *{category}* set to {format_amount(result.amount, currency)} / month.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(BUDGET_CATEGORY, None)
    await update.effective_message.reply_text("❌ Cancelled.", reply_markup=main_menu())
    return ConversationHandler.END


# --- Remove budget ----------------------------------------------------------

async def start_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    async with user_session(update) as (session, user):
        budgets = await BudgetService(session).list_budgets(user.id)
    if not budgets:
        await query.edit_message_text("No budgets to remove.", reply_markup=main_menu())
        return
    rows = [
        [InlineKeyboardButton(f"🗑 {b.category}", callback_data=f"brm:{b.category}")]
        for b in budgets
    ]
    await query.edit_message_text(
        "Select a budget to remove:", reply_markup=InlineKeyboardMarkup(rows)
    )


async def do_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, category = parse_cb(query.data)
    async with user_session(update) as (session, user):
        await BudgetService(session).remove_budget(user.id, category)
    await query.answer(f"Removed {category}")
    await show_budget(update, context)


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_set, pattern=r"^budget:set$")],
        states={
            SetBudget.CATEGORY: [CallbackQueryHandler(choose_category, pattern=r"^bcat:")],
            SetBudget.LIMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_limit)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", cancel)],
        name="set_budget",
        persistent=False,
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(start_remove, pattern=r"^budget:remove$"))
    app.add_handler(CallbackQueryHandler(do_remove, pattern=r"^brm:"))
