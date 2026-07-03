"""Customer / farmer schemas."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Accepts digits, spaces, +, -, parentheses; 7..20 chars.
_PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


def _validate_phone(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not _PHONE_RE.match(value):
        raise ValueError("Telefon raqami noto'g'ri formatda")
    return value


class CustomerBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    passport: str | None = Field(default=None, max_length=30)
    description: str | None = None
    is_active: bool = True

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str | None) -> str | None:
        return _validate_phone(v)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    passport: str | None = Field(default=None, max_length=30)
    description: str | None = None
    is_active: bool | None = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str | None) -> str | None:
        return _validate_phone(v)


class CustomerOut(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CustomerDebtSummary(BaseModel):
    """Aggregate debt figures for a customer."""

    total_debt: Decimal
    total_paid: Decimal
    remaining: Decimal
    active_debts: int
    overdue_debts: int


class PurchaseHistoryItem(BaseModel):
    """One sale in a customer's purchase history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    date: datetime
    total_amount: Decimal
    paid_amount: Decimal
    payment_status: str


class CustomerDetail(CustomerOut):
    """Customer with debt summary and recent purchases."""

    debt_summary: CustomerDebtSummary
    purchases: list[PurchaseHistoryItem] = Field(default_factory=list)
