"""Debt (Qarz) schemas."""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DebtStatus
from app.schemas.payment import PaymentMethodBrief
from app.schemas.stock_out import CustomerBrief


class DebtCreate(BaseModel):
    """Create a standalone debt (not tied to a specific sale)."""

    customer_id: int
    amount: Decimal = Field(gt=0)
    due_date: date_type | None = None
    start_date: date_type | None = None
    note: str | None = None


class DebtPaymentCreate(BaseModel):
    """Record a repayment toward a debt."""

    amount: Decimal = Field(gt=0)
    payment_method_id: int
    note: str | None = None


class DebtDueDateUpdate(BaseModel):
    """Edit a debt's due date (API_SPECIFICATION.md §11)."""

    due_date: date_type | None = None


class DebtPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    debt_id: int
    amount: Decimal
    payment_method_id: int
    date: datetime
    note: str | None = None
    payment_method: PaymentMethodBrief | None = None


class DebtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    store_id: int | None = None
    customer_id: int
    stock_out_id: int | None = None
    amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    start_date: date_type
    due_date: date_type | None = None
    status: DebtStatus
    note: str | None = None
    created_at: datetime
    customer: CustomerBrief | None = None


class DebtDetail(DebtOut):
    """Debt including its repayment history."""

    payments: list[DebtPaymentOut] = Field(default_factory=list)
