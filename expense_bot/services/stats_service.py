"""Analytical statistics across a user's spending history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.schemas import CategoryTotal, MerchantTotal
from ..db.repositories import ExpenseRepository
from .dates import month_range, week_range


@dataclass
class Statistics:
    highest_category: CategoryTotal | None
    lowest_category: CategoryTotal | None
    most_frequent_category: CategoryTotal | None
    average_expense: float
    transactions: int
    week_total: float
    month_total: float
    top_merchants: list[MerchantTotal]


class StatsService:
    """Provides insight-level aggregates over a wide time window."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.expenses = ExpenseRepository(session)

    async def overview(
        self, user_id: int, today: date | None = None, window_days: int = 365
    ) -> Statistics:
        from datetime import timedelta

        end = today or date.today()
        start = end - timedelta(days=window_days)

        by_category = await self.expenses.totals_by_category(user_id, start, end)
        total = await self.expenses.total_between(user_id, start, end)
        count = await self.expenses.count_between(user_id, start, end)
        top_merchants = await self.expenses.totals_by_merchant(user_id, start, end)

        highest = by_category[0] if by_category else None
        lowest = by_category[-1] if by_category else None
        most_frequent = (
            max(by_category, key=lambda c: c.count) if by_category else None
        )

        w_start, w_end = week_range(end)
        m_start, m_end = month_range(end)

        return Statistics(
            highest_category=highest,
            lowest_category=lowest,
            most_frequent_category=most_frequent,
            average_expense=round(total / count, 2) if count else 0.0,
            transactions=count,
            week_total=await self.expenses.total_between(user_id, w_start, w_end),
            month_total=await self.expenses.total_between(user_id, m_start, m_end),
            top_merchants=top_merchants,
        )
