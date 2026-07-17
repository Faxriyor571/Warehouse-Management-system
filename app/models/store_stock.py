"""Per-store on-hand stock (DATABASE_DESIGN.md §3.8 / §11).

One row per ``(store, product)`` pair holding the current maintained balance.
This is the successor to the legacy ``products.quantity`` scalar, partitioned
by store. It is mutated only through ``inventory_service.apply_movement`` so
the balance and the ``stock_movements`` ledger can never disagree.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

QTY = Numeric(14, 3)


class StoreStock(Base):
    """Current on-hand quantity of a product at a store."""

    __tablename__ = "store_stock"

    __table_args__ = (
        UniqueConstraint("store_id", "product_id", name="uq_store_stock_store_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StoreStock store={self.store_id} product={self.product_id} qty={self.quantity}>"
