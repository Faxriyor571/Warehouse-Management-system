"""Supplier model (Yetkazib beruvchi)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.stock_in import StockIn


class Supplier(Base, TimestampMixin, SoftDeleteMixin):
    """A company or person that supplies products to the warehouse."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), index=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsible_person: Mapped[str | None] = mapped_column(String(150), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    stock_ins: Mapped[list["StockIn"]] = relationship(back_populates="supplier")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Supplier {self.name}>"
