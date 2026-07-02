"""Product model."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
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
    """A stock-keeping product held in the warehouse."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)

    # SKU (internal code) and barcode are unique when present.
    sku: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(60), unique=True, index=True, nullable=True)

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    purchase_price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)

    # Reorder threshold; when quantity <= min_quantity the product is "low".
    min_quantity: Mapped[Decimal] = mapped_column(QTY, default=Decimal("0"), nullable=False)
    # Current on-hand stock. Updated by stock-in / stock-out operations.
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
