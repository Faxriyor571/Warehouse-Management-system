"""Setting data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.setting import Setting


class CRUDSetting(CRUDBase[Setting]):
    """CRUD operations for :class:`Setting`."""

    def get_by_key(self, db: Session, key: str) -> Setting | None:
        return db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()

    def upsert(
        self, db: Session, key: str, value: str | None, description: str | None = None
    ) -> Setting:
        obj = self.get_by_key(db, key)
        if obj is None:
            obj = Setting(key=key, value=value, description=description)
            db.add(obj)
        else:
            obj.value = value
            if description is not None:
                obj.description = description
            db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj


setting = CRUDSetting(Setting)
