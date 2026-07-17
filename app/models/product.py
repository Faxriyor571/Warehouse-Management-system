"""Product model."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.stock_in import StockInItem
    from app.models.stock_out import StockOutItem
    from app.models.unit import Unit

# Money uses 2 decimal places; quantities allow 3 (e.g. kilograms).
MONEY = Numeric(14, 2)
QTY = Numeric(14, 3)


class Product(Base, TimestampMixin, SoftDeleteMixin):
    """A catalogue product owned by a company.

    Company-scoped per DATABASE_DESIGN.md §3.7: ``sku`` (and ``barcode`` when
    present) are unique within the company. Rows with ``company_id IS NULL``
    belong to the legacy single-tenant scope during the migration and stay
    unique among themselves via the partial indexes below.
    """

    __tablename__ = "products"

    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_products_company_sku"),
        UniqueConstraint("company_id", "barcode", name="uq_products_company_barcode"),
        Index(
            "uq_products_null_company_sku",
            "sku",
            unique=True,
            sqlite_where=text("company_id IS NULL"),
            postgresql_where=text("company_id IS NULL"),
        ),
        Index(
            "uq_products_null_company_barcode",
            "barcode",
            unique=True,
            sqlite_where=text("company_id IS NULL AND barcode IS NOT NULL"),
            postgresql_where=text("company_id IS NULL AND barcode IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)

    sku: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(60), index=True, nullable=True)

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    purchase_price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)

    # --- TRANSITIONAL / DEPRECATED inventory columns ---
    # Per DATABASE_DESIGN.md §3.7 on-hand stock does not belong on Product; it
    # moves to per-store ``store_stock`` in the Inventory phase. These columns
    # are kept only so the still-legacy inventory/reporting modules (stock-in,
    # stock-out, dashboard, reports) keep working unchanged. No catalogue code
    # written in this phase reads or writes them — treat them as deprecated.
    min_quantity: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), nullable=False, index=True)

    image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # --- Relationships ---
    category: Mapped["Category"] = relationship(back_populates="products", lazy="joined")
    unit: Mapped["Unit"] = relationship(back_populates="products", lazy="joined")
    stock_in_items: Mapped[list["StockInItem"]] = relationship(back_populates="product")
    stock_out_items: Mapped[list["StockOutItem"]] = relationship(back_populates="product")

    # ------------------------------------------------------------------
    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.min_quantity

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.sku} {self.name}>"
