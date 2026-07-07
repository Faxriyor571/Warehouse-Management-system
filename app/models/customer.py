"""Customer / farmer model (Fermer / Mijoz)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CustomerType
from app.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.debt import Debt
    from app.models.stock_out import StockOut


class Customer(Base, TimestampMixin, SoftDeleteMixin):
    """A farmer or customer who receives products from the warehouse.

    ``customer_type`` is the single minimal addition required by Sales to
    enforce SRS rule #18 (legal-entity price override); it is nullable
    because the legacy /customers creation flow does not set it, and a NULL
    value is treated the same as Individual (no override) — this is not a
    Customers migration.
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    customer_type: Mapped[CustomerType | None] = mapped_column(
        SAEnum(CustomerType, name="customer_type"), nullable=True
    )
    phone: Mapped[str | None] = mapped_column(String(30), index=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    passport: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    stock_outs: Mapped[list["StockOut"]] = relationship(back_populates="customer")
    debts: Mapped[list["Debt"]] = relationship(back_populates="customer")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Customer {self.full_name}>"
