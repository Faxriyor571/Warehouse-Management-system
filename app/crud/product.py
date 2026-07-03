"""Product data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.product import Product


class CRUDProduct(CRUDBase[Product]):
    """CRUD operations for :class:`Product`."""

    def get_by_sku(self, db: Session, sku: str) -> Product | None:
        stmt = select(Product).where(Product.sku == sku, Product.deleted_at.is_(None))
        return db.execute(stmt).scalar_one_or_none()

    def get_by_barcode(self, db: Session, barcode: str) -> Product | None:
        stmt = select(Product).where(
            Product.barcode == barcode, Product.deleted_at.is_(None)
        )
        return db.execute(stmt).scalar_one_or_none()


product = CRUDProduct(Product)
