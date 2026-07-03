"""Product schemas."""
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


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=60)
    barcode: str | None = Field(default=None, max_length=60)
    category_id: int
    unit_id: int
    purchase_price: Decimal = Field(default=Decimal("0"), ge=0)
    sale_price: Decimal = Field(default=Decimal("0"), ge=0)
    min_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    description: str | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    """Create payload. Initial on-hand quantity is optional (defaults to 0)."""

    quantity: Decimal = Field(default=Decimal("0"), ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=60)
    barcode: str | None = Field(default=None, max_length=60)
    category_id: int | None = None
    unit_id: int | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    min_quantity: Decimal | None = Field(default=None, ge=0)
    description: str | None = None
    is_active: bool | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: Decimal
    image: str | None = None
    is_low_stock: bool = False
    created_at: datetime
    updated_at: datetime
    category: CategoryOut | None = None
    unit: UnitOut | None = None
