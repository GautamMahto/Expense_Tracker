"""Pydantic schemas for validation and data transfer between layers."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentMethod(StrEnum):
    CASH = "Cash"
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    UPI = "UPI"
    BANK_TRANSFER = "Bank Transfer"
    WALLET = "Wallet"
    OTHER = "Other"


class ExportFormat(StrEnum):
    PDF = "PDF"
    CSV = "CSV"
    EXCEL = "Excel"


class UserProfile(BaseModel):
    """A Telegram user's profile / preferences."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_user_id: int
    username: str | None = None
    full_name: str | None = None
    timezone: str = "UTC"
    currency: str = "USD"
    default_payment_method: str | None = None
    language: str = "en"
    export_format: str = "CSV"
    reminder_time: str | None = None  # "HH:MM" 24h local time, None = off
    created_at: datetime | None = None


class ExpenseCreate(BaseModel):
    """Validated payload for creating an expense."""

    amount: float = Field(..., gt=0, description="Positive monetary amount")
    currency: str = Field(..., min_length=2, max_length=8)
    category: str = Field(..., min_length=1)
    merchant: str | None = None
    expense_date: date
    payment_method: str | None = None
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("merchant", "notes")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    expense_id: int
    user_id: int
    amount: float
    currency: str
    category: str
    merchant: str | None
    expense_date: date
    payment_method: str | None
    notes: str | None
    created_at: datetime | None = None


class BudgetCreate(BaseModel):
    category: str = Field(..., min_length=1)
    monthly_limit: float = Field(..., gt=0)


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_id: int
    user_id: int
    category: str
    monthly_limit: float


class CategoryTotal(BaseModel):
    category: str
    total: float
    count: int


class MerchantTotal(BaseModel):
    merchant: str
    total: float
    count: int
