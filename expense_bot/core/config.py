"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from environment variables (and a local ``.env`` file in
    development). Secrets such as ``BOT_TOKEN`` must never be committed.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: str = Field(..., alias="BOT_TOKEN")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./expense_bot.db",
        alias="DATABASE_URL",
    )

    # Application
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_currency: str = Field(default="USD", alias="DEFAULT_CURRENCY")
    default_timezone: str = Field(default="UTC", alias="DEFAULT_TIMEZONE")

    # Reminders
    reminders_enabled: bool = Field(default=True, alias="REMINDERS_ENABLED")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()  # type: ignore[call-arg]
