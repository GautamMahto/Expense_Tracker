"""Report generation (today / weekly / monthly)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.schemas import CategoryTotal, ExpenseRead, MerchantTotal
from ..db.repositories import ExpenseRepository
from .budget_service import BudgetService, BudgetStatus
from .dates import (
    days_elapsed_in_month,
    month_range,
    today_range,
    week_range,
)


@dataclass
class DailyReport:
    day: date
    total: float
    expenses: list[ExpenseRead]


@dataclass
class WeeklyReport:
    start: date
    end: date
    total: float
    average_daily: float
    highest: ExpenseRead | None
    by_category: list[CategoryTotal]


@dataclass
class MonthlyReport:
    start: date
    end: date
    total: float
    transactions: int
    daily_average: float
    largest: ExpenseRead | None
    by_category: list[CategoryTotal]
    top_merchants: list[MerchantTotal]
    budgets: list[BudgetStatus] = field(default_factory=list)


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.expenses = ExpenseRepository(session)
        self.budgets = BudgetService(session)

    async def daily(self, user_id: int, day: date | None = None) -> DailyReport:
        start, end = today_range(day)
        rows = await self.expenses.list_between(user_id, start, end)
        total = await self.expenses.total_between(user_id, start, end)
        return DailyReport(
            day=start,
            total=total,
            expenses=[ExpenseRead.model_validate(r) for r in rows],
        )

    async def weekly(self, user_id: int, today: date | None = None) -> WeeklyReport:
        start, end = week_range(today)
        total = await self.expenses.total_between(user_id, start, end)
        highest = await self.expenses.largest_between(user_id, start, end)
        by_category = await self.expenses.totals_by_category(user_id, start, end)
        return WeeklyReport(
            start=start,
            end=end,
            total=total,
            average_daily=round(total / 7, 2),
            highest=ExpenseRead.model_validate(highest) if highest else None,
            by_category=by_category,
        )

    async def monthly(self, user_id: int, today: date | None = None) -> MonthlyReport:
        start, end = month_range(today)
        total = await self.expenses.total_between(user_id, start, end)
        count = await self.expenses.count_between(user_id, start, end)
        largest = await self.expenses.largest_between(user_id, start, end)
        by_category = await self.expenses.totals_by_category(user_id, start, end)
        top_merchants = await self.expenses.totals_by_merchant(user_id, start, end)
        budgets = await self.budgets.all_statuses(user_id)

        elapsed = max(days_elapsed_in_month(today), 1)
        return MonthlyReport(
            start=start,
            end=end,
            total=total,
            transactions=count,
            daily_average=round(total / elapsed, 2),
            largest=ExpenseRead.model_validate(largest) if largest else None,
            by_category=by_category,
            top_merchants=top_merchants,
            budgets=budgets,
        )
