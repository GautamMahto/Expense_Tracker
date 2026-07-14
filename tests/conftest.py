"""Shared pytest fixtures. Uses an isolated in-memory SQLite database."""

from __future__ import annotations

import os

# Config requires BOT_TOKEN; set a dummy before any app import.
os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from expense_bot.db.models import Base


@pytest_asyncio.fixture
async def session():
    """Provide a committed-per-test async session against a fresh schema."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()
