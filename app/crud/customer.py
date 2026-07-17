"""Customer data-access operations. Every query is scoped to a company.

``company_id=None`` resolves the legacy single-tenant scope
(``company_id IS NULL``); a concrete ``company_id`` resolves within that
company — company-wide, no store scoping (DATABASE_DESIGN.md §3.11/§10).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.customer import Customer
from app.models.enums import CustomerType
from app.utils.pagination import PageParams


class CRUDCustomer(CRUDBase[Customer]):
    """CRUD operations for :class:`Customer`, always company-scoped."""

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return Customer.company_id.is_(None)
        return Customer.company_id == company_id

    def get_for_company(
        self, db: Session, customer_id: int, company_id: int | None
    ) -> Customer | None:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.deleted_at.is_(None),
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
        customer_type: CustomerType | None = None,
    ) -> tuple[Sequence[Customer], int]:
        filters: list[Any] = [self._company_filter(company_id)]
        if customer_type is not None:
            filters.append(Customer.customer_type == customer_type)
        return self.list(
            db,
            page_params=page_params,
            search=search,
            search_fields=[Customer.full_name, Customer.phone],
            filters=filters,
            order_by=Customer.full_name.asc(),
        )


customer = CRUDCustomer(Customer)
