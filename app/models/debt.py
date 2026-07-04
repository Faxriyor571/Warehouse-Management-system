"""Debt models (Qarzdorlar).

A ``Debt`` is created when a sale is not fully paid. Repayments are recorded as
``DebtPayment`` rows, keeping a full history. The debt tracks remaining amount,
due date and status.
"""
from __future__ import annotations

# The date type is aliased so it can never be shadowed by a field/attribute
# named ``date`` when SQLAlchemy / Pydantic evaluate string annotations under
# ``from __future__ import annotations``.
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import DebtStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.payment_method import PaymentMethod
    from app.models.stock_out import StockOut
    from app.models.user import User

MONEY = Numeric(14, 2)


class Debt(Base, TimestampMixin):
    """An outstanding debt owed by a customer for a sale."""

    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stock_out_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_outs.id", ondelete="SET NULL"), nullable=True, unique=True, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Original debt principal.
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    # Stored, denormalised remaining amount kept in sync on each payment.
    remaining_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    start_date: Mapped[date_type] = mapped_column(Date, server_default=func.current_date(), nullable=False)
    due_date: Mapped[date_type | None] = mapped_column(Date, nullable=True, index=True)

    status: Mapped[DebtStatus] = mapped_column(
        SAEnum(DebtStatus, name="debt_status"),
        default=DebtStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    customer: Mapped["Customer"] = relationship(back_populates="debts", lazy="joined")
    stock_out: Mapped["StockOut | None"] = relationship(back_populates="debt")
    created_by: Mapped["User"] = relationship(lazy="joined")
    payments: Mapped[list["DebtPayment"]] = relationship(
        back_populates="debt",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DebtPayment.date",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Debt customer={self.customer_id} remaining={self.remaining_amount}>"


class DebtPayment(Base, TimestampMixin):
    """A single repayment toward a debt."""

    __tablename__ = "debt_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    debt_id: Mapped[int] = mapped_column(
        ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_method_id: Mapped[int] = mapped_column(
        ForeignKey("payment_methods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    debt: Mapped["Debt"] = relationship(back_populates="payments")
    payment_method: Mapped["PaymentMethod"] = relationship(
        back_populates="debt_payments", lazy="joined"
    )
    created_by: Mapped["User"] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DebtPayment debt={self.debt_id} amount={self.amount}>"
