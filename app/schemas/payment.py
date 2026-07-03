"""Payment schemas (for sales / chiqim)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    """A payment line supplied at sale time (supports mixed payments)."""

    payment_method_id: int
    amount: Decimal = Field(gt=0)
    note: str | None = None


class PaymentMethodBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_out_id: int
    payment_method_id: int
    amount: Decimal
    date: datetime
    note: str | None = None
    payment_method: PaymentMethodBrief | None = None
