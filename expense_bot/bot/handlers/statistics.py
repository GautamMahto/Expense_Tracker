"""Statistics / insights handler."""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ...services.stats_service import StatsService
from .. import formatting
from ..deps import user_session
from ..keyboards import back_to_menu


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with user_session(update) as (session, user):
        stats = await StatsService(session).overview(user.id)
        text = formatting.statistics(stats, user.currency)

    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu()
        )
    else:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_to_menu()
        )
