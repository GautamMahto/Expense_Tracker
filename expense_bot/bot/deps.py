"""Helpers bridging Telegram updates to the service layer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update

from ..db.models import User
from ..db.session import session_scope
from ..services.user_service import UserService


@asynccontextmanager
async def user_session(update: Update) -> AsyncIterator[tuple[AsyncSession, User]]:
    """Open a DB session and resolve (creating if needed) the current user.

    Implicit authentication: the Telegram ``user_id`` uniquely identifies the
    user, and every query downstream is scoped to ``user.id``.
    """
    tg_user = update.effective_user
    if tg_user is None:  # pragma: no cover - defensive
        raise RuntimeError("Update has no effective user")

    async with session_scope() as session:
        service = UserService(session)
        user = await service.get_or_create(
            telegram_user_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
        )
        yield session, user
