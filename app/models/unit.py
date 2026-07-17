"""Unit of measurement model (Birlik)."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Unit(Base, TimestampMixin):
    """A unit of measurement, company-scoped per DATABASE_DESIGN.md §3.6.

    A name is unique within its company. Rows with ``company_id IS NULL``
    belong to the legacy single-tenant scope during the migration and remain
    unique among themselves via the partial index below.
    """

    __tablename__ = "units"

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_units_company_name"),
        Index(
            "uq_units_null_company_name",
            "name",
            unique=True,
            sqlite_where=text("company_id IS NULL"),
            postgresql_where=text("company_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)
    # Base-unit (kg) equivalent, e.g. 50 for "1 bag = 50 kg" (SRS rule #8).
    conversion_factor: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="unit")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Unit {self.name}>"
