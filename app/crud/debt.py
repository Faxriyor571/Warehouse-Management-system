"""Debt data-access operations. Every query is scoped to a company.

``company_id=None`` resolves the legacy single-tenant scope
(``company_id IS NULL``); a concrete ``company_id`` resolves within that
company.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.debt import Debt, DebtPayment
from app.models.enums import DebtStatus
from app.utils.pagination import PageParams


class CRUDDebt(CRUDBase[Debt]):
    """CRUD operations for :class:`Debt`, always company-scoped."""

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return Debt.company_id.is_(None)
        return Debt.company_id == company_id

    def get_for_scope(
        self, db: Session, debt_id: int, company_id: int | None, *, store_id: int | None = None
    ) -> Debt | None:
        stmt = select(Debt).where(Debt.id == debt_id, self._company_filter(company_id))
        if store_id is not None:
            stmt = stmt.where(Debt.store_id == store_id)
        return db.execute(stmt).scalar_one_or_none()

    def list_for_scope(
        self,
        db: Session,
        company_id: int | None,
        *,
        page_params: PageParams,
        store_id: int | None = None,
        customer_id: int | None = None,
        status: DebtStatus | None = None,
        only_open: bool = False,
        due_before: date_type | None = None,
        due_after: date_type | None = None,
    ) -> tuple[Sequence[Debt], int]:
        filters: list[Any] = [self._company_filter(company_id)]
        if store_id is not None:
            filters.append(Debt.store_id == store_id)
        if customer_id is not None:
            filters.append(Debt.customer_id == customer_id)
        if status is not None:
            filters.append(Debt.status == status)
        if only_open:
            filters.append(Debt.remaining_amount > 0)
        if due_before is not None:
            filters.append(Debt.due_date <= due_before)
        if due_after is not None:
            filters.append(Debt.due_date >= due_after)
        return self.list(
            db,
            page_params=page_params,
            filters=filters,
            order_by=Debt.due_date.asc().nulls_last(),
        )


class CRUDDebtPayment(CRUDBase[DebtPayment]):
    """CRUD operations for :class:`DebtPayment`."""


debt = CRUDDebt(Debt)
debt_payment = CRUDDebtPayment(DebtPayment)
