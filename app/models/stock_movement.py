"""Append-only inventory ledger (DATABASE_DESIGN.md §3.9 / §11).

Every quantity-affecting event is recorded here as a signed delta, tagged with
its ``movement_type`` and a polymorphic ``reference_type``/``reference_id``
pointing back to the originating document. The invariant
``store_stock.quantity == sum(stock_movements.quantity_delta)`` per
``(store, product)`` makes the ledger the auditable source of truth behind the
maintained balance.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import MovementType

QTY = Numeric(14, 3)


class StockMovement(Base):
    """A single, immutable inventory movement."""

    __tablename__ = "stock_movements"

    __table_args__ = (
        Index("ix_stock_movements_store_product_created", "store_id", "product_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Denormalized company id (defense-in-depth tenant scoping — §10).
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    movement_type: Mapped[MovementType] = mapped_column(
        SAEnum(MovementType, name="movement_type"), nullable=False, index=True
    )
    # Signed: + for stock in / return, − for a sale.
    quantity_delta: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    # Polymorphic pointer to the originating document; intentionally not an
    # enforced FK (it can reference stock_in / sale / sales_return).
    reference_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StockMovement {self.movement_type} {self.quantity_delta} store={self.store_id}>"
