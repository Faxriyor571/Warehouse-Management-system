"""Stock-in data-access operations. Reads are company/store scoped."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.stock_in import StockIn
from app.utils.pagination import PageParams


class CRUDStockIn(CRUDBase[StockIn]):
    """CRUD operations for :class:`StockIn`, always company-scoped.

    ``company_id=None`` resolves the legacy single-tenant scope
    (``company_id IS NULL``); a concrete ``company_id`` resolves within that
    company.
    """

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return StockIn.company_id.is_(None)
        return StockIn.company_id == company_id

    def get_for_scope(
        self,
        db: Session,
        stock_in_id: int,
        company_id: int | None,
        *,
        store_id: int | None = None,
    ) -> StockIn | None:
        stmt = select(StockIn).where(
            StockIn.id == stock_in_id, self._company_filter(company_id)
        )
        if store_id is not None:
            stmt = stmt.where(StockIn.store_id == store_id)
        return db.execute(stmt).scalar_one_or_none()

    def list_for_scope(
        self,
        db: Session,
        company_id: int | None,
        *,
        page_params: PageParams,
        store_id: int | None = None,
        supplier_id: int | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[StockIn], int]:
        filters: list = [self._company_filter(company_id)]
        if store_id is not None:
            filters.append(StockIn.store_id == store_id)
        if supplier_id is not None:
            filters.append(StockIn.supplier_id == supplier_id)
        if date_from is not None:
            filters.append(func.date(StockIn.date) >= date_from)
        if date_to is not None:
            filters.append(func.date(StockIn.date) <= date_to)
        return self.list(
            db,
            page_params=page_params,
            search=search,
            search_fields=[StockIn.reference],
            filters=filters,
            order_by=StockIn.date.desc(),
        )


stock_in = CRUDStockIn(StockIn)
