"""Supplier data-access operations. Every query is scoped to a company.

``company_id=None`` resolves the legacy single-tenant scope
(``company_id IS NULL``); a concrete ``company_id`` resolves within that
company — company-wide, no store scoping (mirrors Customers).
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.supplier import Supplier
from app.utils.pagination import PageParams


class CRUDSupplier(CRUDBase[Supplier]):
    """CRUD operations for :class:`Supplier`, always company-scoped."""

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return Supplier.company_id.is_(None)
        return Supplier.company_id == company_id

    def get_for_company(
        self, db: Session, supplier_id: int, company_id: int | None
    ) -> Supplier | None:
        stmt = select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.deleted_at.is_(None),
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
    ) -> tuple[Sequence[Supplier], int]:
        return self.list(
            db,
            page_params=page_params,
            search=search,
            search_fields=[Supplier.name, Supplier.phone, Supplier.responsible_person],
            filters=[self._company_filter(company_id)],
            order_by=Supplier.name.asc(),
        )


supplier = CRUDSupplier(Supplier)
