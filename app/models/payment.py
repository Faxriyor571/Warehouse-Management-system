"""Payment model for sales (Chiqim to'lovlari).

A sale can have multiple payments, enabling mixed payments (e.g. half Click,
half cash). Each payment references the method used.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.payment_method import PaymentMethod
    from app.models.stock_out import StockOut
    from app.models.user import User

MONEY = Numeric(14, 2)


class Payment(Base, TimestampMixin):
    """A single payment applied to a sale document."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_out_id: Mapped[int] = mapped_column(
        ForeignKey("stock_outs.id", ondelete="CASCADE"), nullable=False, index=True
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

    stock_out: Mapped["StockOut"] = relationship(back_populates="payments")
    payment_method: Mapped["PaymentMethod"] = relationship(
        back_populates="payments", lazy="joined"
    )
    created_by: Mapped["User"] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Payment sale={self.stock_out_id} amount={self.amount}>"
