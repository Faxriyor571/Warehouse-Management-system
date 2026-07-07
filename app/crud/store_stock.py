"""Store-stock data-access operations. All reads are company/store scoped."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Row, func, or_, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.store import Store
from app.models.store_stock import StoreStock
from app.utils.pagination import PageParams


class CRUDStoreStock:
    """Data access for :class:`StoreStock` balances."""

    def get(self, db: Session, store_id: int, product_id: int) -> StoreStock | None:
        stmt = select(StoreStock).where(
            StoreStock.store_id == store_id, StoreStock.product_id == product_id
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_for_store(
        self,
        db: Session,
        store_id: int,
        *,
        page_params: PageParams,
        search: str | None = None,
    ) -> tuple[Sequence[Row[Any]], int]:
        """Rows of ``(product_id, product_name, sku, quantity)`` for one store."""
        base = (
            select(
                StoreStock.product_id.label("product_id"),
                Product.name.label("product_name"),
                Product.sku.label("sku"),
                StoreStock.quantity.label("quantity"),
            )
            .join(Product, StoreStock.product_id == Product.id)
            .where(StoreStock.store_id == store_id, Product.deleted_at.is_(None))
        )
        if search:
            like = f"%{search.strip()}%"
            base = base.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))

        total = db.execute(
            select(func.count()).select_from(base.order_by(None).subquery())
        ).scalar_one()
        rows = db.execute(
            base.order_by(Product.name.asc())
            .offset(page_params.offset)
            .limit(page_params.limit)
        ).all()
        return rows, total

    def list_company_wide(
        self,
        db: Session,
        company_id: int,
        *,
        page_params: PageParams,
        search: str | None = None,
    ) -> tuple[Sequence[Row[Any]], int]:
        """Per-product totals summed across every store in the company."""
        base = (
            select(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.sku.label("sku"),
                func.coalesce(func.sum(StoreStock.quantity), 0).label("quantity"),
            )
            .join(StoreStock, StoreStock.product_id == Product.id)
            .join(Store, StoreStock.store_id == Store.id)
            .where(Store.company_id == company_id, Product.deleted_at.is_(None))
            .group_by(Product.id, Product.name, Product.sku)
        )
        if search:
            like = f"%{search.strip()}%"
            base = base.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))

        total = db.execute(
            select(func.count()).select_from(base.order_by(None).subquery())
        ).scalar_one()
        rows = db.execute(
            base.order_by(Product.name.asc())
            .offset(page_params.offset)
            .limit(page_params.limit)
        ).all()
        return rows, total

    def cross_store_for_product(
        self, db: Session, company_id: int, product_id: int
    ) -> Sequence[Row[Any]]:
        """Rows of ``(store_id, store_name, quantity)`` across the company's stores.

        Quantity only — never joins money/partner tables (SRS rule #4).
        """
        stmt = (
            select(
                Store.id.label("store_id"),
                Store.name.label("store_name"),
                StoreStock.quantity.label("quantity"),
            )
            .join(Store, StoreStock.store_id == Store.id)
            .where(Store.company_id == company_id, StoreStock.product_id == product_id)
            .order_by(Store.id.asc())
        )
        return db.execute(stmt).all()


store_stock = CRUDStoreStock()
