"""Budget configuration and utilisation checks."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.schemas import BudgetRead
from ..db.repositories import BudgetRepository, ExpenseRepository
from .dates import month_range


@dataclass
class BudgetStatus:
    category: str
    monthly_limit: float
    spent: float

    @property
    def remaining(self) -> float:
        return self.monthly_limit - self.spent

    @property
    def exceeded(self) -> bool:
        return self.spent > self.monthly_limit

    @property
    def utilisation(self) -> float:
        if self.monthly_limit <= 0:
            return 0.0
        return self.spent / self.monthly_limit


class BudgetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.budgets = BudgetRepository(session)
        self.expenses = ExpenseRepository(session)

    async def set_budget(
        self, user_id: int, category: str, monthly_limit: float
    ) -> BudgetRead:
        budget = await self.budgets.upsert(user_id, category, monthly_limit)
        return BudgetRead.model_validate(budget)

    async def remove_budget(self, user_id: int, category: str) -> bool:
        return await self.budgets.delete(user_id, category)

    async def list_budgets(self, user_id: int) -> list[BudgetRead]:
        budgets = await self.budgets.list_for_user(user_id)
        return [BudgetRead.model_validate(b) for b in budgets]

    async def status_for_category(
        self, user_id: int, category: str
    ) -> BudgetStatus | None:
        budget = await self.budgets.get(user_id, category)
        if budget is None:
            return None
        start, end = month_range()
        spent = await self.expenses.category_total_for_period(
            user_id, category, start, end
        )
        return BudgetStatus(
            category=category, monthly_limit=budget.monthly_limit, spent=spent
        )

    async def all_statuses(self, user_id: int) -> list[BudgetStatus]:
        start, end = month_range()
        statuses: list[BudgetStatus] = []
        for budget in await self.budgets.list_for_user(user_id):
            spent = await self.expenses.category_total_for_period(
                user_id, budget.category, start, end
            )
            statuses.append(
                BudgetStatus(
                    category=budget.category,
                    monthly_limit=budget.monthly_limit,
                    spent=spent,
                )
            )
        return statuses
