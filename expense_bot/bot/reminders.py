"""Configurable daily reminders via python-telegram-bot's JobQueue.

Each user's ``reminder_time`` (local ``HH:MM``) schedules a daily job that,
if no expense was logged that day, nudges them. Timezone-aware per user.
"""

from __future__ import annotations

from datetime import time
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from ..core.logging import get_logger
from ..db.session import session_scope
from ..services.expense_service import ExpenseService
from ..services.user_service import UserService

logger = get_logger(__name__)

REMINDER_JOB_PREFIX = "reminder_user_"


def _job_name(telegram_user_id: int) -> str:
    return f"{REMINDER_JOB_PREFIX}{telegram_user_id}"


async def _send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data or {}
    telegram_user_id = data["telegram_user_id"]
    db_user_id = data["db_user_id"]

    async with session_scope() as session:
        total = await ExpenseService(session).total_for_day(db_user_id)

    if total > 0:
        return  # already logged something today

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yes", callback_data="menu:add"),
                InlineKeyboardButton("🚫 No", callback_data="reminder:dismiss"),
            ]
        ]
    )
    await context.bot.send_message(
        chat_id=telegram_user_id,
        text="🔔 Did you spend anything today?",
        reply_markup=keyboard,
    )


async def dismiss_reminder(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer("Okay, nothing logged today. 👍")
    await update.callback_query.edit_message_text("👍 No expenses today. See you tomorrow!")


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(hour=int(hh), minute=int(mm))


def schedule_user_reminder(
    app: Application,
    *,
    telegram_user_id: int,
    db_user_id: int,
    reminder_time: str,
    timezone: str,
) -> None:
    """(Re)schedule a single user's daily reminder job."""
    if app.job_queue is None:  # pragma: no cover - job-queue extra missing
        logger.warning("JobQueue unavailable; reminders disabled")
        return

    for job in app.job_queue.get_jobs_by_name(_job_name(telegram_user_id)):
        job.schedule_removal()

    try:
        tzinfo = ZoneInfo(timezone)
    except Exception:  # noqa: BLE001 - fall back to UTC on bad tz
        tzinfo = ZoneInfo("UTC")

    run_at = _parse_hhmm(reminder_time).replace(tzinfo=tzinfo)
    app.job_queue.run_daily(
        _send_reminder,
        time=run_at,
        name=_job_name(telegram_user_id),
        data={"telegram_user_id": telegram_user_id, "db_user_id": db_user_id},
    )
    logger.info(
        "Scheduled reminder for user %s at %s %s",
        telegram_user_id,
        reminder_time,
        timezone,
    )


def cancel_user_reminder(app: Application, telegram_user_id: int) -> None:
    if app.job_queue is None:
        return
    for job in app.job_queue.get_jobs_by_name(_job_name(telegram_user_id)):
        job.schedule_removal()


async def load_all_reminders(app: Application) -> None:
    """Schedule reminders for every user who has one configured (called at boot)."""
    if app.job_queue is None:
        logger.warning("JobQueue unavailable; skipping reminder scheduling")
        return
    async with session_scope() as session:
        users = await UserService(session).users_with_reminders()
        for user in users:
            if user.reminder_time:
                schedule_user_reminder(
                    app,
                    telegram_user_id=user.telegram_user_id,
                    db_user_id=user.id,
                    reminder_time=user.reminder_time,
                    timezone=user.timezone,
                )
    logger.info("Loaded reminders for %d user(s)", len(users))


def register(app: Application) -> None:
    app.add_handler(CallbackQueryHandler(dismiss_reminder, pattern=r"^reminder:dismiss$"))
