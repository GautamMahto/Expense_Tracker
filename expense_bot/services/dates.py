"""Date-range helpers for reporting periods."""

from __future__ import annotations

import calendar
from datetime import date, timedelta


def today_range(today: date | None = None) -> tuple[date, date]:
    d = today or date.today()
    return d, d


def week_range(today: date | None = None) -> tuple[date, date]:
    """Monday-to-Sunday week containing ``today``."""
    d = today or date.today()
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def month_range(today: date | None = None) -> tuple[date, date]:
    d = today or date.today()
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, 1), date(d.year, d.month, last_day)


def days_elapsed_in_month(today: date | None = None) -> int:
    d = today or date.today()
    return d.day
