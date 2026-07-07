"""Setting data-access operations. Every query is scoped to a company.

``company_id=None`` resolves the legacy single-tenant scope
(``company_id IS NULL``); a concrete ``company_id`` resolves within that
company. This mirrors the uniqueness constraint on the model.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.setting import Setting


class CRUDSetting(CRUDBase[Setting]):
    """CRUD operations for :class:`Setting`, always company-scoped."""

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return Setting.company_id.is_(None)
        return Setting.company_id == company_id

    def list_for_company(self, db: Session, company_id: int | None) -> Sequence[Setting]:
        stmt = select(Setting).where(self._company_filter(company_id)).order_by(Setting.key.asc())
        return db.execute(stmt).scalars().all()

    def get_by_key_for_company(self, db: Session, key: str, company_id: int | None) -> Setting | None:
        stmt = select(Setting).where(Setting.key == key, self._company_filter(company_id))
        return db.execute(stmt).scalar_one_or_none()

    def upsert(
        self, db: Session, company_id: int | None, key: str, value: str | None, *, commit: bool = True
    ) -> Setting:
        obj = self.get_by_key_for_company(db, key, company_id)
        if obj is None:
            obj = Setting(company_id=company_id, key=key, value=value)
            db.add(obj)
        else:
            obj.value = value
            db.add(obj)
        if commit:
            db.commit()
            db.refresh(obj)
        return obj


setting = CRUDSetting(Setting)
