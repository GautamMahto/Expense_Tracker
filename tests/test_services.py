"""Integration tests for the service layer against a real (in-memory) DB."""

from __future__ import annotations

from datetime import date

from expense_bot.core.schemas import ExpenseCreate
from expense_bot.services.budget_service import BudgetService
from expense_bot.services.expense_service import ExpenseService
from expense_bot.services.report_service import ReportService
from expense_bot.services.stats_service import StatsService
from expense_bot.services.user_service import UserService


async def _make_user(session, tid: int = 111):
    user = await UserService(session).get_or_create(
        telegram_user_id=tid, username="tester", full_name="Test User"
    )
    await session.commit()
    return user


def _expense(**kwargs) -> ExpenseCreate:
    base = dict(
        amount=100.0,
        currency="USD",
        category="Food",
        merchant="Cafe",
        expense_date=date.today(),
        payment_method="Cash",
        notes=None,
    )
    base.update(kwargs)
    return ExpenseCreate(**base)


async def test_user_isolation(session):
    u1 = await _make_user(session, 1)
    u2 = await _make_user(session, 2)
    svc = ExpenseService(session)
    await svc.create(u1.id, _expense(amount=50))
    await svc.create(u2.id, _expense(amount=999))
    await session.commit()

    assert await svc.total_for_day(u1.id) == 50
    assert await svc.total_for_day(u2.id) == 999


async def test_daily_report_totals(session):
    user = await _make_user(session)
    svc = ExpenseService(session)
    await svc.create(user.id, _expense(amount=10, category="Food"))
    await svc.create(user.id, _expense(amount=15, category="Transport"))
    await session.commit()

    report = await ReportService(session).daily(user.id)
    assert report.total == 25
    assert len(report.expenses) == 2


async def test_budget_alert_on_exceed(session):
    user = await _make_user(session)
    await BudgetService(session).set_budget(user.id, "Food", 30)
    await session.commit()

    svc = ExpenseService(session)
    result = await svc.create(user.id, _expense(amount=25, category="Food"))
    assert result.budget_alert is None

    result = await svc.create(user.id, _expense(amount=25, category="Food"))
    assert result.budget_alert is not None
    assert result.budget_alert.exceeded
    assert result.budget_alert.spent == 50


async def test_monthly_report_breakdown(session):
    user = await _make_user(session)
    svc = ExpenseService(session)
    await svc.create(user.id, _expense(amount=40, category="Food", merchant="A"))
    await svc.create(user.id, _expense(amount=60, category="Shopping", merchant="B"))
    await session.commit()

    report = await ReportService(session).monthly(user.id)
    assert report.total == 100
    assert report.transactions == 2
    categories = {c.category: c.total for c in report.by_category}
    assert categories == {"Shopping": 60, "Food": 40}


async def test_statistics_overview(session):
    user = await _make_user(session)
    svc = ExpenseService(session)
    await svc.create(user.id, _expense(amount=40, category="Food"))
    await svc.create(user.id, _expense(amount=60, category="Travel"))
    await session.commit()

    stats = await StatsService(session).overview(user.id)
    assert stats.transactions == 2
    assert stats.average_expense == 50
    assert stats.highest_category.category == "Travel"
