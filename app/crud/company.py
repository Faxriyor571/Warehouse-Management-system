"""Company data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.company import Company


class CRUDCompany(CRUDBase[Company]):
    """CRUD operations for :class:`Company`."""

    def get_by_slug(self, db: Session, slug: str) -> Company | None:
        stmt = select(Company).where(Company.slug == slug)
        return db.execute(stmt).scalar_one_or_none()


company = CRUDCompany(Company)
