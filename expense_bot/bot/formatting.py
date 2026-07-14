"""Message text builders for reports and confirmations (presentation layer)."""

from __future__ import annotations

from datetime import date

from ..core.currency import format_amount
from ..core.schemas import ExpenseRead
from ..services.budget_service import BudgetStatus
from ..services.report_service import DailyReport, MonthlyReport, WeeklyReport
from ..services.stats_service import Statistics


def _fmt_date(d: date) -> str:
    return d.strftime("%d %b %Y")


def expense_confirmation(e: ExpenseRead) -> str:
    lines = [
        "✅ *Expense Saved Successfully*",
        "",
        f"*Amount:* {format_amount(e.amount, e.currency)}",
        f"*Category:* {e.category}",
    ]
    if e.merchant:
        lines.append(f"*Merchant:* {e.merchant}")
    lines.append(f"*Date:* {_fmt_date(e.expense_date)}")
    if e.payment_method:
        lines.append(f"*Payment:* {e.payment_method}")
    if e.notes:
        lines.append(f"*Notes:* {e.notes}")
    return "\n".join(lines)


def budget_alert(status: BudgetStatus, currency: str) -> str:
    over_by = status.spent - status.monthly_limit
    return (
        f"⚠️ You have exceeded your *{status.category}* budget by "
        f"{format_amount(over_by, currency)}.\n"
        f"Spent {format_amount(status.spent, currency)} of "
        f"{format_amount(status.monthly_limit, currency)}."
    )


def daily_report(report: DailyReport, currency: str) -> str:
    if not report.expenses:
        return f"📊 *{_fmt_date(report.day)}*\n\nNo expenses recorded today."
    lines = [f"📊 *Today — {_fmt_date(report.day)}*", ""]
    for e in report.expenses:
        merchant = f" · {e.merchant}" if e.merchant else ""
        lines.append(f"• {format_amount(e.amount, e.currency)} — {e.category}{merchant}")
    lines.append("")
    lines.append(f"*Total:* {format_amount(report.total, currency)}")
    return "\n".join(lines)


def weekly_report(report: WeeklyReport, currency: str) -> str:
    lines = [
        "🗓 *Weekly Report*",
        f"_{_fmt_date(report.start)} – {_fmt_date(report.end)}_",
        "",
        f"*Total spent:* {format_amount(report.total, currency)}",
        f"*Avg / day:* {format_amount(report.average_daily, currency)}",
    ]
    if report.highest:
        lines.append(
            f"*Highest:* {format_amount(report.highest.amount, report.highest.currency)}"
            f" ({report.highest.category})"
        )
    if report.by_category:
        lines.append("")
        lines.append("*By category:*")
        for c in report.by_category:
            lines.append(f"• {c.category}: {format_amount(c.total, currency)}")
    return "\n".join(lines)


def monthly_report(report: MonthlyReport, currency: str) -> str:
    lines = [
        "📅 *Monthly Report*",
        f"_{_fmt_date(report.start)} – {_fmt_date(report.end)}_",
        "",
        f"*Total spending:* {format_amount(report.total, currency)}",
        f"*Transactions:* {report.transactions}",
        f"*Daily average:* {format_amount(report.daily_average, currency)}",
    ]
    if report.largest:
        lines.append(
            f"*Largest expense:* {format_amount(report.largest.amount, report.largest.currency)}"
            f" ({report.largest.category})"
        )
    if report.by_category:
        lines.append("")
        lines.append("*Spending by category:*")
        for c in report.by_category:
            lines.append(f"• {c.category}: {format_amount(c.total, currency)}")
    if report.top_merchants:
        lines.append("")
        lines.append("*Top merchants:*")
        for m in report.top_merchants:
            lines.append(f"• {m.merchant}: {format_amount(m.total, currency)}")
    if report.budgets:
        lines.append("")
        lines.append("*Budget utilisation:*")
        for b in report.budgets:
            pct = round(b.utilisation * 100)
            flag = " ⚠️" if b.exceeded else ""
            lines.append(
                f"• {b.category}: {format_amount(b.spent, currency)} / "
                f"{format_amount(b.monthly_limit, currency)} ({pct}%){flag}"
            )
    return "\n".join(lines)


def statistics(stats: Statistics, currency: str) -> str:
    if stats.transactions == 0:
        return "📈 *Statistics*\n\nNo expenses recorded yet. Add one to see insights!"
    lines = ["📈 *Statistics* (last 12 months)", ""]
    if stats.highest_category:
        lines.append(
            f"*Top category:* {stats.highest_category.category} "
            f"({format_amount(stats.highest_category.total, currency)})"
        )
    if stats.lowest_category and stats.lowest_category != stats.highest_category:
        lines.append(
            f"*Lowest category:* {stats.lowest_category.category} "
            f"({format_amount(stats.lowest_category.total, currency)})"
        )
    if stats.most_frequent_category:
        lines.append(
            f"*Most frequent:* {stats.most_frequent_category.category} "
            f"({stats.most_frequent_category.count}×)"
        )
    lines.append(f"*Average expense:* {format_amount(stats.average_expense, currency)}")
    lines.append(f"*This week:* {format_amount(stats.week_total, currency)}")
    lines.append(f"*This month:* {format_amount(stats.month_total, currency)}")
    if stats.top_merchants:
        lines.append("")
        lines.append("*Top merchants:*")
        for m in stats.top_merchants:
            lines.append(f"• {m.merchant}: {format_amount(m.total, currency)}")
    return "\n".join(lines)
