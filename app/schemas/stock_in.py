"""Stock-in (Kirim) schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductBrief


class StockInItemCreate(BaseModel):
    """One inbound line to add."""

    product_id: int
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(ge=0, description="Sotib olish narxi (birlik uchun)")


class StockInCreate(BaseModel):
    """Payload to create an inbound delivery document."""

    supplier_id: int | None = None
    date: datetime | None = None
    note: str | None = None
    items: list[StockInItemCreate] = Field(min_length=1)


class StockInItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: Decimal
    price: Decimal
    subtotal: Decimal
    product: ProductBrief | None = None


class SupplierBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class StockInOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    supplier_id: int | None = None
    created_by_id: int
    date: datetime
    total_amount: Decimal
    note: str | None = None
    created_at: datetime
    supplier: SupplierBrief | None = None
    created_by: UserBrief | None = None
    items: list[StockInItemOut] = Field(default_factory=list)
