"""Expense creation and retrieval, with budget-alert side effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.schemas import ExpenseCreate, ExpenseRead
from ..db.repositories import ExpenseRepository
from .budget_service import BudgetService, BudgetStatus
from .dates import today_range


@dataclass
class SaveResult:
    expense: ExpenseRead
    budget_alert: BudgetStatus | None  # set when the category budget is now exceeded


class ExpenseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.expenses = ExpenseRepository(session)
        self.budgets = BudgetService(session)

    async def create(self, user_id: int, data: ExpenseCreate) -> SaveResult:
        expense = await self.expenses.add(user_id, data)
        read = ExpenseRead.model_validate(expense)

        alert: BudgetStatus | None = None
        status = await self.budgets.status_for_category(user_id, data.category)
        if status is not None and status.exceeded:
            alert = status

        return SaveResult(expense=read, budget_alert=alert)

    async def delete(self, user_id: int, expense_id: int) -> bool:
        return await self.expenses.delete(user_id, expense_id)

    async def list_for_day(
        self, user_id: int, day: date | None = None
    ) -> list[ExpenseRead]:
        start, end = today_range(day)
        rows = await self.expenses.list_between(user_id, start, end)
        return [ExpenseRead.model_validate(r) for r in rows]

    async def list_between(
        self, user_id: int, start: date, end: date
    ) -> list[ExpenseRead]:
        rows = await self.expenses.list_between(user_id, start, end)
        return [ExpenseRead.model_validate(r) for r in rows]

    async def total_for_day(self, user_id: int, day: date | None = None) -> float:
        start, end = today_range(day)
        return await self.expenses.total_between(user_id, start, end)
