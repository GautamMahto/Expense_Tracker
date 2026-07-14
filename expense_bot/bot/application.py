"""Assemble the python-telegram-bot Application and register handlers.

Handler registration order matters: active conversations must be able to
intercept their own inputs before the catch-all natural-language handler, so
the NLP conversation is always registered last.
"""

from __future__ import annotations

from telegram.ext import Application, ApplicationBuilder

from ..core.config import Settings, get_settings
from ..core.logging import get_logger
from ..db.session import init_models, session_scope
from ..services.user_service import ensure_categories_seeded
from . import reminders
from .handlers import add_expense, budget, menu, nlp, reports
from .handlers import settings as settings_handlers

logger = get_logger(__name__)


async def _post_init(app: Application) -> None:
    """Run once after the Application starts: schema, seed data, reminders."""
    settings: Settings = app.bot_data["settings"]
    if settings.is_sqlite:
        # Dev convenience: create tables directly. Production uses Alembic.
        await init_models()
    async with session_scope() as session:
        await ensure_categories_seeded(session)
    if settings.reminders_enabled:
        await reminders.load_all_reminders(app)
    logger.info("Bot initialised (environment=%s)", settings.environment)


def build_application(settings: Settings | None = None) -> Application:
    settings = settings or get_settings()

    app = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .post_init(_post_init)
        .build()
    )
    app.bot_data["settings"] = settings

    # 1) Conversations that own specific callback entry points come first.
    app.add_handler(add_expense.build_conversation())
    app.add_handler(budget.build_conversation())
    app.add_handler(settings_handlers.build_conversation())

    # 2) Top-level menu commands and router.
    menu.register(app)

    # 3) Feature callback handlers.
    budget.register(app)
    settings_handlers.register(app)
    reports.register(app)
    reminders.register(app)

    # 4) Catch-all natural-language handler LAST so it never steals
    #    inputs belonging to an active conversation.
    app.add_handler(nlp.build_conversation())

    return app
