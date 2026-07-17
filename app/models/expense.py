"""Expense model (API_SPECIFICATION.md §12, DATABASE_DESIGN.md §3.22).

Immutable once created (no PUT/DELETE) — only ``created_at`` is tracked, no
``updated_at``. ``company_id``/``store_id`` nullable for the legacy
single-tenant scope (Option A); the tenant path always sets both.
"""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ExpenseType

if TYPE_CHECKING:
    from app.models.user import User

MONEY = Numeric(14, 2)


class Expense(Base):
    """An operational expense recorded at a store (SRS §4.7)."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    expense_type: Mapped[ExpenseType] = mapped_column(
        SAEnum(ExpenseType, name="expense_type"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date_type] = mapped_column(Date, server_default=func.current_date(), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    created_by: Mapped["User"] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Expense {self.expense_type} {self.amount}>"
