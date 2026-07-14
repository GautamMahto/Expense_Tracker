"""Application entrypoint — runs the bot with long polling."""

from __future__ import annotations

from telegram import Update

from .bot.application import build_application
from .core.config import get_settings
from .core.logging import configure_logging, get_logger


def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    application = build_application(settings)

    logger.info("Starting Expense Tracker bot (long polling)…")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    run()
