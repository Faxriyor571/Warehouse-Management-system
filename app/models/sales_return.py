"""Sale return models (API_SPECIFICATION.md §9, DATABASE_DESIGN.md §3.16/§3.17).

A ``SalesReturn`` reverses part or all of a sale: it restores inventory at the
original sale price and reduces any linked debt, without ever modifying the
original ``StockOut`` record (which stays an immutable historical document).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.stock_out import StockOutItem

MONEY = Numeric(14, 2)
QTY = Numeric(14, 3)


class SalesReturn(Base):
    """Header of a sale-return document.

    Company/store scoped, mirroring ``StockOut``: ``reference`` is unique
    within its store (§6, same reasoning as sales). No ``updated_at`` — a
    return, like a sale, is never modified once created (§3.16 lists only
    ``created_at``).
    """

    __tablename__ = "sales_returns"

    __table_args__ = (
        UniqueConstraint("store_id", "reference", name="uq_sales_returns_store_reference"),
        Index(
            "uq_sales_returns_null_store_reference",
            "reference",
            unique=True,
            sqlite_where=text("store_id IS NULL"),
            postgresql_where=text("store_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    stock_out_id: Mapped[int] = mapped_column(
        ForeignKey("stock_outs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    reference: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list["SalesReturnItem"]] = relationship(
        back_populates="sales_return",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SalesReturn {self.reference}>"


class SalesReturnItem(Base):
    """A single returned line, tied back to the exact original sale line."""

    __tablename__ = "sales_return_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sales_return_id: Mapped[int] = mapped_column(
        ForeignKey("sales_returns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_out_item_id: Mapped[int] = mapped_column(
        ForeignKey("stock_out_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    # Always copied from the original sale line — never re-entered.
    price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    sales_return: Mapped["SalesReturn"] = relationship(back_populates="items")
    stock_out_item: Mapped["StockOutItem"] = relationship(lazy="joined")
    product: Mapped["Product"] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SalesReturnItem stock_out_item={self.stock_out_item_id} qty={self.quantity}>"
