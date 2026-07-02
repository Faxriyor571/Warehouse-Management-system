"""Stock-in (Kirim) models.

A ``StockIn`` document represents one inbound delivery from a supplier and can
contain multiple ``StockInItem`` lines. Applying a stock-in increases product
on-hand quantities.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.supplier import Supplier
    from app.models.user import User

MONEY = Numeric(14, 2)
QTY = Numeric(14, 3)


class StockIn(Base, TimestampMixin):
    """Header of an inbound delivery document."""

    __tablename__ = "stock_ins"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Human readable document number, e.g. "IN-2026-000123".
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)

    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    supplier: Mapped["Supplier"] = relationship(back_populates="stock_ins", lazy="joined")
    created_by: Mapped["User"] = relationship(lazy="joined")
    items: Mapped[list["StockInItem"]] = relationship(
        back_populates="stock_in",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StockIn {self.reference}>"


class StockInItem(Base):
    """A single product line within a stock-in document."""

    __tablename__ = "stock_in_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_in_id: Mapped[int] = mapped_column(
        ForeignKey("stock_ins.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)  # purchase price per unit
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    stock_in: Mapped["StockIn"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="stock_in_items", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StockInItem product={self.product_id} qty={self.quantity}>"
