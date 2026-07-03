"""Role and permission data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.role import Permission, Role


class CRUDRole(CRUDBase[Role]):
    """CRUD operations for :class:`Role`."""

    def get_by_name(self, db: Session, name: str) -> Role | None:
        return db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()


class CRUDPermission(CRUDBase[Permission]):
    """CRUD operations for :class:`Permission`."""

    def get_by_code(self, db: Session, code: str) -> Permission | None:
        return db.execute(
            select(Permission).where(Permission.code == code)
        ).scalar_one_or_none()

    def get_by_codes(self, db: Session, codes: list[str]) -> list[Permission]:
        if not codes:
            return []
        stmt = select(Permission).where(Permission.code.in_(codes))
        return list(db.execute(stmt).scalars().all())


role = CRUDRole(Role)
permission = CRUDPermission(Permission)
