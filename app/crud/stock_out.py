"""Sales (stock-out) data-access operations. Reads are company/store scoped."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.enums import PaymentStatus
from app.models.stock_out import StockOut
from app.utils.pagination import PageParams


class CRUDStockOut(CRUDBase[StockOut]):
    """CRUD operations for :class:`StockOut`, always company-scoped.

    ``company_id=None`` resolves the legacy single-tenant scope
    (``company_id IS NULL``); a concrete ``company_id`` resolves within that
    company.
    """

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return StockOut.company_id.is_(None)
        return StockOut.company_id == company_id

    def get_for_scope(
        self,
        db: Session,
        stock_out_id: int,
        company_id: int | None,
        *,
        store_id: int | None = None,
    ) -> StockOut | None:
        stmt = select(StockOut).where(
            StockOut.id == stock_out_id, self._company_filter(company_id)
        )
        if store_id is not None:
            stmt = stmt.where(StockOut.store_id == store_id)
        return db.execute(stmt).scalar_one_or_none()

    def list_for_scope(
        self,
        db: Session,
        company_id: int | None,
        *,
        page_params: PageParams,
        store_id: int | None = None,
        customer_id: int | None = None,
        payment_status: PaymentStatus | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[StockOut], int]:
        filters: list = [self._company_filter(company_id)]
        if store_id is not None:
            filters.append(StockOut.store_id == store_id)
        if customer_id is not None:
            filters.append(StockOut.customer_id == customer_id)
        if payment_status is not None:
            filters.append(StockOut.payment_status == payment_status)
        if date_from is not None:
            filters.append(func.date(StockOut.date) >= date_from)
        if date_to is not None:
            filters.append(func.date(StockOut.date) <= date_to)
        return self.list(
            db,
            page_params=page_params,
            search=search,
            search_fields=[StockOut.reference],
            filters=filters,
            order_by=StockOut.date.desc(),
        )


stock_out = CRUDStockOut(StockOut)
