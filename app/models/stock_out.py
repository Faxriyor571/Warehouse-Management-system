"""Stock-out (Chiqim) models.

A ``StockOut`` document represents a sale/dispatch to a customer and can hold
multiple ``StockOutItem`` lines. Applying a stock-out decreases product
on-hand quantities and can generate payments and/or a debt.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PaymentStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.debt import Debt
    from app.models.payment import Payment
    from app.models.product import Product
    from app.models.user import User

MONEY = Numeric(14, 2)
QTY = Numeric(14, 3)


class StockOut(Base, TimestampMixin):
    """Header of an outbound sale document (the "Sales" module, API §9).

    Company/store scoped (DATABASE_DESIGN.md §3.14/§6): ``reference`` is
    unique **within its store** (not company — receipts are store-printed).
    ``company_id``/``store_id`` are nullable during the migration — rows
    created through the legacy single-tenant admin have them NULL and remain
    unique among themselves via the partial index below.
    """

    __tablename__ = "stock_outs"

    __table_args__ = (
        UniqueConstraint("store_id", "reference", name="uq_stock_outs_store_reference"),
        Index(
            "uq_stock_outs_null_store_reference",
            "reference",
            unique=True,
            sqlite_where=text("store_id IS NULL"),
            postgresql_where=text("store_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), index=True, nullable=False)

    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Sum of line subtotals before the document-level discount.
    subtotal: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    # Document-level discount amount (absolute value, not percentage).
    discount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    # Final payable amount = subtotal - discount.
    total_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    # Amount actually paid (sum of payments).
    paid_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)

    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.UNPAID,
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    customer: Mapped["Customer"] = relationship(back_populates="stock_outs", lazy="joined")
    created_by: Mapped["User"] = relationship(lazy="joined")
    items: Mapped[list["StockOutItem"]] = relationship(
        back_populates="stock_out",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="stock_out",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    debt: Mapped["Debt | None"] = relationship(
        back_populates="stock_out",
        uselist=False,
    )

    @property
    def remaining_amount(self) -> Decimal:
        return self.total_amount - self.paid_amount

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StockOut {self.reference}>"


class StockOutItem(Base):
    """A single product line within a stock-out document."""

    __tablename__ = "stock_out_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_out_id: Mapped[int] = mapped_column(
        ForeignKey("stock_outs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    quantity: Mapped[Decimal] = mapped_column(QTY, nullable=False)
    price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)  # sale price per unit
    discount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    stock_out: Mapped["StockOut"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="stock_out_items", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StockOutItem product={self.product_id} qty={self.quantity}>"
