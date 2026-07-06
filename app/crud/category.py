"""Category data-access operations. Every query is scoped to a company.

``company_id=None`` resolves the legacy single-tenant scope
(``company_id IS NULL``); a concrete ``company_id`` resolves within that
company. This mirrors the uniqueness constraints on the model.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.category import Category
from app.utils.pagination import PageParams


class CRUDCategory(CRUDBase[Category]):
    """CRUD operations for :class:`Category`, always company-scoped."""

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return Category.company_id.is_(None)
        return Category.company_id == company_id

    def get_for_company(
        self, db: Session, category_id: int, company_id: int | None
    ) -> Category | None:
        stmt = select(Category).where(
            Category.id == category_id,
            Category.deleted_at.is_(None),
            self._company_filter(company_id),
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_name_for_company(
        self, db: Session, name: str, company_id: int | None
    ) -> Category | None:
        stmt = select(Category).where(
            Category.name == name,
            Category.deleted_at.is_(None),
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
    ) -> tuple[Sequence[Category], int]:
        return self.list(
            db,
            page_params=page_params,
            search=search,
            search_fields=[Category.name],
            filters=[self._company_filter(company_id)],
        )


category = CRUDCategory(Category)
