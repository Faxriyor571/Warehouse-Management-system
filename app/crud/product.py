"""Product data-access operations. Every query is scoped to a company.

``company_id=None`` resolves the legacy single-tenant scope
(``company_id IS NULL``); a concrete ``company_id`` resolves within that
company. This mirrors the uniqueness constraints on the model.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.product import Product
from app.utils.pagination import PageParams


class CRUDProduct(CRUDBase[Product]):
    """CRUD operations for :class:`Product`, always company-scoped."""

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return Product.company_id.is_(None)
        return Product.company_id == company_id

    # --- Uniqueness checks: deliberately DO NOT exclude soft-deleted rows ---
    # The DB uniqueness constraints reserve an sku/barcode even for a
    # soft-deleted product (they carry no ``deleted_at`` qualifier), so these
    # checks must see soft-deleted rows too; otherwise a re-create would pass
    # the service check and then fail at the DB with a 500 instead of a clean
    # 409. Display reads (``get_for_company``/``list_for_company``) exclude
    # soft-deleted rows as usual.
    def get_by_sku_for_company(
        self, db: Session, sku: str, company_id: int | None
    ) -> Product | None:
        stmt = select(Product).where(Product.sku == sku, self._company_filter(company_id))
        return db.execute(stmt).scalar_one_or_none()

    def get_by_barcode_for_company(
        self, db: Session, barcode: str, company_id: int | None
    ) -> Product | None:
        stmt = select(Product).where(
            Product.barcode == barcode, self._company_filter(company_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    # --- Display reads: exclude soft-deleted rows ---
    def get_for_company(
        self, db: Session, product_id: int, company_id: int | None
    ) -> Product | None:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
            self._company_filter(company_id),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_for_company(
        self,
        db: Session,
        company_id: int | None,
        *,
        page_params: PageParams,
        search: str | None = None,
        category_id: int | None = None,
    ) -> tuple[Sequence[Product], int]:
        filters: list[Any] = [self._company_filter(company_id)]
        if category_id is not None:
            filters.append(Product.category_id == category_id)
        return self.list(
            db,
            page_params=page_params,
            search=search,
            search_fields=[Product.name, Product.sku, Product.barcode],
            filters=filters,
            order_by=Product.name.asc(),
        )


product = CRUDProduct(Product)
