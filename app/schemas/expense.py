"""Expense schemas (API_SPECIFICATION.md §12)."""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ExpenseType


class ExpenseCreate(BaseModel):
    """Payload to record an expense.

    ``store_id`` is required for a CEO (the incurring store) and omitted by a
    Seller (resolved from the token, SRS rule #12).
    """

    store_id: int | None = None
    expense_type: ExpenseType
    amount: Decimal = Field(gt=0)
    description: str = Field(min_length=1)
    date: date_type | None = None


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    store_id: int | None = None
    created_by_id: int
    expense_type: ExpenseType
    amount: Decimal
    description: str
    date: date_type
    created_at: datetime
    created_by: UserBrief | None = None
