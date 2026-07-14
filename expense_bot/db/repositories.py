"""Data-access repositories. All queries are scoped to a single user."""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.schemas import CategoryTotal, ExpenseCreate, MerchantTotal
from .models import Budget, Category, Expense, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        full_name: str | None,
        currency: str,
        timezone: str,
    ) -> User:
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            full_name=full_name,
            currency=currency,
            timezone=timezone,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_fields(self, user: User, **fields: object) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        await self.session.flush()
        return user

    async def all_with_reminders(self) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.reminder_time.is_not(None))
        )
        return list(result.scalars().all())


class ExpenseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user_id: int, data: ExpenseCreate) -> Expense:
        expense = Expense(
            user_id=user_id,
            amount=data.amount,
            currency=data.currency,
            category=data.category,
            merchant=data.merchant,
            expense_date=data.expense_date,
            payment_method=data.payment_method,
            notes=data.notes,
        )
        self.session.add(expense)
        await self.session.flush()
        return expense

    async def delete(self, user_id: int, expense_id: int) -> bool:
        result = await self.session.execute(
            delete(Expense).where(
                Expense.expense_id == expense_id, Expense.user_id == user_id
            )
        )
        return result.rowcount > 0

    async def list_between(
        self, user_id: int, start: date, end: date
    ) -> list[Expense]:
        result = await self.session.execute(
            select(Expense)
            .where(
                Expense.user_id == user_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .order_by(Expense.expense_date.desc(), Expense.expense_id.desc())
        )
        return list(result.scalars().all())

    async def total_between(self, user_id: int, start: date, end: date) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
        )
        return float(result.scalar_one())

    async def category_total_for_period(
        self, user_id: int, category: str, start: date, end: date
    ) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user_id,
                Expense.category == category,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
        )
        return float(result.scalar_one())

    async def totals_by_category(
        self, user_id: int, start: date, end: date
    ) -> list[CategoryTotal]:
        result = await self.session.execute(
            select(
                Expense.category,
                func.sum(Expense.amount),
                func.count(Expense.expense_id),
            )
            .where(
                Expense.user_id == user_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .group_by(Expense.category)
            .order_by(func.sum(Expense.amount).desc())
        )
        return [
            CategoryTotal(category=row[0], total=float(row[1]), count=int(row[2]))
            for row in result.all()
        ]

    async def totals_by_merchant(
        self, user_id: int, start: date, end: date, limit: int = 5
    ) -> list[MerchantTotal]:
        result = await self.session.execute(
            select(
                Expense.merchant,
                func.sum(Expense.amount),
                func.count(Expense.expense_id),
            )
            .where(
                Expense.user_id == user_id,
                Expense.merchant.is_not(None),
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .group_by(Expense.merchant)
            .order_by(func.sum(Expense.amount).desc())
            .limit(limit)
        )
        return [
            MerchantTotal(merchant=row[0], total=float(row[1]), count=int(row[2]))
            for row in result.all()
        ]

    async def count_between(self, user_id: int, start: date, end: date) -> int:
        result = await self.session.execute(
            select(func.count(Expense.expense_id)).where(
                Expense.user_id == user_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
        )
        return int(result.scalar_one())

    async def largest_between(
        self, user_id: int, start: date, end: date
    ) -> Expense | None:
        result = await self.session.execute(
            select(Expense)
            .where(
                Expense.user_id == user_id,
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .order_by(Expense.amount.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class BudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int, category: str) -> Budget | None:
        result = await self.session.execute(
            select(Budget).where(
                Budget.user_id == user_id, Budget.category == category
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: int, category: str, monthly_limit: float) -> Budget:
        budget = await self.get(user_id, category)
        if budget is None:
            budget = Budget(
                user_id=user_id, category=category, monthly_limit=monthly_limit
            )
            self.session.add(budget)
        else:
            budget.monthly_limit = monthly_limit
        await self.session.flush()
        return budget

    async def list_for_user(self, user_id: int) -> list[Budget]:
        result = await self.session.execute(
            select(Budget).where(Budget.user_id == user_id).order_by(Budget.category)
        )
        return list(result.scalars().all())

    async def delete(self, user_id: int, category: str) -> bool:
        result = await self.session.execute(
            delete(Budget).where(
                Budget.user_id == user_id, Budget.category == category
            )
        )
        return result.rowcount > 0


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(Category.category_id)))
        return int(result.scalar_one())

    async def bulk_create(self, items: list[tuple[str, str]]) -> None:
        self.session.add_all(
            [Category(category_name=name, icon=icon) for name, icon in items]
        )
        await self.session.flush()
