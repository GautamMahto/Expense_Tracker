"""User settings: currency, timezone, payment, export format, reminders."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

from ...core.currency import KNOWN_CODES
from ...core.schemas import ExportFormat, PaymentMethod
from ...services.user_service import UserService
from ..deps import user_session
from ..keyboards import main_menu, settings_menu
from ..states import Settings as SettingsState
from ..states import parse_cb

EDIT_FIELD = "settings_field"
_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def _summary(user) -> str:
    reminder = user.reminder_time or "off"
    payment = user.default_payment_method or "—"
    return (
        "⚙️ *Settings*\n\n"
        f"💱 *Currency:* {user.currency}\n"
        f"🌍 *Timezone:* {user.timezone}\n"
        f"💳 *Default payment:* {payment}\n"
        f"📤 *Export format:* {user.export_format}\n"
        f"⏰ *Daily reminder:* {reminder}\n\n"
        "Tap an item to change it."
    )


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with user_session(update) as (_, user):
        text = _summary(user)
    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=settings_menu()
        )
    else:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=settings_menu()
        )


# --- Choice-based settings (payment / export) -------------------------------

async def choose_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton(m.value, callback_data=f"setpay:{m.value}")]
        for m in PaymentMethod
    ]
    await query.edit_message_text(
        "Choose your default payment method:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def save_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, method = parse_cb(query.data)
    async with user_session(update) as (session, user):
        await UserService(session).update_preferences(user, default_payment_method=method)
    await query.answer("Saved")
    await show_settings(update, context)


async def choose_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    buttons = [
        [InlineKeyboardButton(f.value, callback_data=f"setexp:{f.value}")]
        for f in ExportFormat
    ]
    await query.edit_message_text(
        "Choose your default export format:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def save_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, fmt = parse_cb(query.data)
    async with user_session(update) as (session, user):
        await UserService(session).update_preferences(user, export_format=fmt)
    await query.answer("Saved")
    await show_settings(update, context)


# --- Text-based settings conversation (currency / timezone / reminder) ------

_PROMPTS = {
    "currency": "Send your 3-letter currency code, e.g. `USD`, `INR`, `EUR`.",
    "timezone": "Send your timezone, e.g. `Asia/Kolkata` or `Europe/London`.",
    "reminder": "Send a daily reminder time as `HH:MM` (24h), or `off` to disable.",
}


async def start_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, field = parse_cb(query.data)
    context.user_data[EDIT_FIELD] = field
    await query.answer()
    await query.edit_message_text(_PROMPTS[field], parse_mode=ParseMode.MARKDOWN)
    return SettingsState.AWAIT_VALUE


async def receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.pop(EDIT_FIELD, None)
    value = update.message.text.strip()

    if field == "currency":
        code = value.upper()
        if code not in KNOWN_CODES and not re.fullmatch(r"[A-Z]{3}", code):
            await update.message.reply_text("⚠️ That doesn't look like a currency code.")
            context.user_data[EDIT_FIELD] = "currency"
            return SettingsState.AWAIT_VALUE
        update_kwargs = {"currency": code}
        confirmation = f"💱 Currency set to *{code}*."

    elif field == "timezone":
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, ModuleNotFoundError):
            await update.message.reply_text("⚠️ Unknown timezone. Try `Asia/Kolkata`.")
            context.user_data[EDIT_FIELD] = "timezone"
            return SettingsState.AWAIT_VALUE
        update_kwargs = {"timezone": value}
        confirmation = f"🌍 Timezone set to *{value}*."

    else:  # reminder
        if value.lower() in {"off", "none", "disable"}:
            update_kwargs = {"reminder_time": None}
            confirmation = "⏰ Daily reminder disabled."
        elif _TIME_RE.match(value):
            hh, mm = value.split(":")
            normalised = f"{int(hh):02d}:{mm}"
            update_kwargs = {"reminder_time": normalised}
            confirmation = f"⏰ Daily reminder set for *{normalised}*."
        else:
            await update.message.reply_text("⚠️ Use `HH:MM` (e.g. `21:00`) or `off`.")
            context.user_data[EDIT_FIELD] = "reminder"
            return SettingsState.AWAIT_VALUE

    async with user_session(update) as (session, user):
        await UserService(session).update_preferences(user, **update_kwargs)
        db_user_id, tg_user_id, tz = user.id, user.telegram_user_id, user.timezone

    if field == "reminder":
        from ..reminders import cancel_user_reminder, schedule_user_reminder

        new_time = update_kwargs.get("reminder_time")
        if new_time:
            schedule_user_reminder(
                context.application,
                telegram_user_id=tg_user_id,
                db_user_id=db_user_id,
                reminder_time=new_time,
                timezone=tz,
            )
        else:
            cancel_user_reminder(context.application, tg_user_id)

    await update.message.reply_text(
        confirmation, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(EDIT_FIELD, None)
    await update.effective_message.reply_text("❌ Cancelled.", reply_markup=main_menu())
    return ConversationHandler.END


def build_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_edit, pattern=r"^set:(currency|timezone|reminder)$")
        ],
        states={
            SettingsState.AWAIT_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_value)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", cancel)],
        name="settings",
        persistent=False,
    )


def register(app) -> None:
    app.add_handler(CallbackQueryHandler(choose_payment, pattern=r"^set:payment$"))
    app.add_handler(CallbackQueryHandler(save_payment, pattern=r"^setpay:"))
    app.add_handler(CallbackQueryHandler(choose_export, pattern=r"^set:export$"))
    app.add_handler(CallbackQueryHandler(save_export, pattern=r"^setexp:"))
