"""Unit data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.unit import Unit


class CRUDUnit(CRUDBase[Unit]):
    """CRUD operations for :class:`Unit`."""

    def get_by_name(self, db: Session, name: str) -> Unit | None:
        return db.execute(select(Unit).where(Unit.name == name)).scalar_one_or_none()


unit = CRUDUnit(Unit)
