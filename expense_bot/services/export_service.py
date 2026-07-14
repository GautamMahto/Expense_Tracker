"""Export expenses to CSV (built-in) with hooks for Excel/PDF.

CSV is implemented with the standard library so it always works. Excel and PDF
require the optional ``analytics`` extra (``pandas``/``openpyxl``/matplotlib);
they degrade gracefully with a clear message if the dependency is absent.
"""

from __future__ import annotations

import csv
import io

from ..core.schemas import ExpenseRead

CSV_COLUMNS = [
    "expense_id",
    "expense_date",
    "amount",
    "currency",
    "category",
    "merchant",
    "payment_method",
    "notes",
]


class ExportError(RuntimeError):
    """Raised when an export format is unavailable in this environment."""


def to_csv_bytes(expenses: list[ExpenseRead]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for e in expenses:
        writer.writerow(
            {
                "expense_id": e.expense_id,
                "expense_date": e.expense_date.isoformat(),
                "amount": f"{e.amount:.2f}",
                "currency": e.currency,
                "category": e.category,
                "merchant": e.merchant or "",
                "payment_method": e.payment_method or "",
                "notes": e.notes or "",
            }
        )
    return buffer.getvalue().encode("utf-8")


def to_excel_bytes(expenses: list[ExpenseRead]) -> bytes:
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ExportError(
            "Excel export needs the optional 'analytics' extra: "
            "pip install 'expense-bot[analytics]'"
        ) from exc

    frame = pd.DataFrame(
        [
            {
                "expense_id": e.expense_id,
                "date": e.expense_date,
                "amount": e.amount,
                "currency": e.currency,
                "category": e.category,
                "merchant": e.merchant,
                "payment_method": e.payment_method,
                "notes": e.notes,
            }
            for e in expenses
        ]
    )
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False, sheet_name="Expenses")
    return buffer.getvalue()


def to_pdf_bytes(expenses: list[ExpenseRead]) -> bytes:  # pragma: no cover - hook
    """PDF export hook.

    Left as an extension point: render ``expenses`` to a PDF (e.g. via
    ``matplotlib`` tables or ``reportlab``). Raises until implemented so the
    handler can fall back to CSV.
    """
    raise ExportError("PDF export is not yet implemented; try CSV or Excel.")
