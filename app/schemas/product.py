"""Product schemas (API_SPECIFICATION.md §6)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryOut
from app.schemas.unit import UnitOut


class ProductBrief(BaseModel):
    """Lightweight product representation for embedding in documents."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str


class ProductCreate(BaseModel):
    """Create payload (§6). On-hand quantity is not part of this payload — a new
    product starts with zero stock everywhere until a Stock In is recorded."""

    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=60)
    barcode: str | None = Field(default=None, max_length=60)
    category_id: int
    unit_id: int
    purchase_price: Decimal = Field(default=Decimal("0"), ge=0)
    sale_price: Decimal = Field(default=Decimal("0"), ge=0)
    description: str | None = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=60)
    barcode: str | None = Field(default=None, max_length=60)
    category_id: int | None = None
    unit_id: int | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    description: str | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    barcode: str | None = None
    category_id: int
    unit_id: int
    purchase_price: Decimal
    sale_price: Decimal
    description: str | None = None
    is_active: bool
    image: str | None = None
    # TRANSITIONAL / DEPRECATED: legacy company-global on-hand quantity. The
    # spec's per-store quantity (joined from store_stock) arrives in the
    # Inventory phase; until then this exposes the legacy column so the
    # still-legacy stock-flow keeps functioning. New catalogue code does not
    # rely on it.
    quantity: Decimal
    created_at: datetime
    updated_at: datetime
    category: CategoryOut | None = None
    unit: UnitOut | None = None
