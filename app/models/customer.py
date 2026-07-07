"""Customer / farmer model (Fermer / Mijoz)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
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

    Company-wide (DATABASE_DESIGN.md §3.11/§10): scoped by ``company_id``
    only, no ``store_id`` — any Seller in the company can find/manage any
    company customer. ``company_id`` is nullable for the legacy single-tenant
    flow. No uniqueness constraint is required beyond ``id`` (§6).

    ``customer_type`` is nullable because the legacy ``/customers`` flow does
    not set it (NULL is treated the same as Individual — no price override);
    the tenant path requires it at creation (API_SPECIFICATION.md §10).
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    customer_type: Mapped[CustomerType | None] = mapped_column(
        SAEnum(CustomerType, name="customer_type"), nullable=True, index=True
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
