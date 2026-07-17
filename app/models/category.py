"""Product category model."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Category(Base, TimestampMixin, SoftDeleteMixin):
    """A product category (e.g. "O'g'itlar", "Urug'lar").

    Company-scoped per DATABASE_DESIGN.md §3.5/§6: a name is unique within its
    company. Rows with ``company_id IS NULL`` belong to the legacy
    single-tenant scope during the migration and remain unique among
    themselves via the partial index below (mirroring the ``users`` pattern).
    """

    __tablename__ = "categories"

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_categories_company_name"),
        Index(
            "uq_categories_null_company_name",
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
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category {self.name}>"
