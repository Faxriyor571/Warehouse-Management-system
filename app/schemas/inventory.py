"""Inventory read schemas (API_SPECIFICATION.md §7)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import MovementType


class StoreStockRow(BaseModel):
    """One product's on-hand quantity at the resolved store (or company-wide)."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    sku: str
    quantity: Decimal


class CrossStoreRow(BaseModel):
    """A product's on-hand quantity at one store — the cross-store view.

    Quantity only; no financial or partner data (SRS rule #4).
    """

    model_config = ConfigDict(from_attributes=True)

    store_id: int
    store_name: str
    quantity: Decimal


class StockMovementOut(BaseModel):
    """One row of the append-only inventory ledger."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    product_id: int
    movement_type: MovementType
    quantity_delta: Decimal
    reference_type: str
    reference_id: int | None = None
    created_by: str | None = None
    created_at: datetime
