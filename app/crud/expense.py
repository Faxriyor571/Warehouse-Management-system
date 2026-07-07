"""Expense data-access operations. Reads are company/store scoped."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.enums import ExpenseType
from app.models.expense import Expense
from app.utils.pagination import PageParams


class CRUDExpense(CRUDBase[Expense]):
    """CRUD operations for :class:`Expense`, always company-scoped.

    ``company_id=None`` resolves the legacy single-tenant scope
    (``company_id IS NULL``); a concrete ``company_id`` resolves within that
    company.
    """

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return Expense.company_id.is_(None)
        return Expense.company_id == company_id

    def get_for_scope(
        self, db: Session, expense_id: int, company_id: int | None, *, store_id: int | None = None
    ) -> Expense | None:
        stmt = select(Expense).where(Expense.id == expense_id, self._company_filter(company_id))
        if store_id is not None:
            stmt = stmt.where(Expense.store_id == store_id)
        return db.execute(stmt).scalar_one_or_none()

    def list_for_scope(
        self,
        db: Session,
        company_id: int | None,
        *,
        page_params: PageParams,
        store_id: int | None = None,
        expense_type: ExpenseType | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
    ) -> tuple[Sequence[Expense], int]:
        filters: list = [self._company_filter(company_id)]
        if store_id is not None:
            filters.append(Expense.store_id == store_id)
        if expense_type is not None:
            filters.append(Expense.expense_type == expense_type)
        if date_from is not None:
            filters.append(Expense.date >= date_from)
        if date_to is not None:
            filters.append(Expense.date <= date_to)
        return self.list(
            db,
            page_params=page_params,
            filters=filters,
            order_by=Expense.date.desc(),
        )


expense = CRUDExpense(Expense)
