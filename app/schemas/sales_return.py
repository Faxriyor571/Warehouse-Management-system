"""Sale return schemas (API_SPECIFICATION.md §9)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SalesReturnItemCreate(BaseModel):
    """One returned line. ``price`` is never accepted — it is always copied
    from the original sale line."""

    stock_out_item_id: int
    quantity: Decimal = Field(gt=0)


class SalesReturnCreate(BaseModel):
    """Payload to return part or all of a sale."""

    reason: str | None = None
    items: list[SalesReturnItemCreate] = Field(min_length=1)


class SalesReturnItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_out_item_id: int
    product_id: int
    quantity: Decimal
    price: Decimal
    subtotal: Decimal


class SalesReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    store_id: int | None = None
    stock_out_id: int
    created_by_id: int
    date: datetime
    reason: str | None = None
    total_amount: Decimal
    created_at: datetime
    items: list[SalesReturnItemOut] = Field(default_factory=list)
