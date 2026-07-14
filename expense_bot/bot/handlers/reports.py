"""Report handlers: today, weekly, monthly, and exports."""

from __future__ import annotations

import io

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

from ...services.dates import month_range
from ...services.expense_service import ExpenseService
from ...services.export_service import (
    ExportError,
    to_csv_bytes,
    to_excel_bytes,
    to_pdf_bytes,
)
from ...services.report_service import ReportService
from .. import formatting
from ..deps import user_session
from ..keyboards import report_export_keyboard, reports_menu
from ..states import parse_cb


async def _edit_or_reply(update: Update, text: str, reply_markup) -> None:
    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with user_session(update) as (session, user):
        report = await ReportService(session).daily(user.id)
        text = formatting.daily_report(report, user.currency)
    await _edit_or_reply(update, text, reports_menu())


async def show_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with user_session(update) as (session, user):
        report = await ReportService(session).weekly(user.id)
        text = formatting.weekly_report(report, user.currency)
    await _edit_or_reply(update, text, reports_menu())


async def show_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with user_session(update) as (session, user):
        report = await ReportService(session).monthly(user.id)
        text = formatting.monthly_report(report, user.currency)
    await _edit_or_reply(update, text, report_export_keyboard())


async def report_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, which = parse_cb(update.callback_query.data)
    if which == "today":
        await show_today(update, context)
    elif which == "weekly":
        await show_weekly(update, context)
    elif which == "monthly":
        await show_monthly(update, context)


async def export_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, fmt = parse_cb(query.data)
    await query.answer(f"Preparing {fmt}…")

    start, end = month_range()
    async with user_session(update) as (session, user):
        expenses = await ExpenseService(session).list_between(user.id, start, end)

    if not expenses:
        await query.message.reply_text("Nothing to export for this month yet.")
        return

    stem = f"expenses_{start:%Y_%m}"
    try:
        if fmt == "CSV":
            data, filename = to_csv_bytes(expenses), f"{stem}.csv"
        elif fmt == "Excel":
            data, filename = to_excel_bytes(expenses), f"{stem}.xlsx"
        else:  # PDF
            data, filename = to_pdf_bytes(expenses), f"{stem}.pdf"
    except ExportError as exc:
        await query.message.reply_text(f"⚠️ {exc}")
        return

    buffer = io.BytesIO(data)
    buffer.name = filename
    await query.message.reply_document(document=buffer, filename=filename)


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(report_router, pattern=r"^report:"))
    app.add_handler(CallbackQueryHandler(export_router, pattern=r"^export:"))
