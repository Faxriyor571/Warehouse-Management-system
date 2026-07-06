"""User data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.user import User


class CRUDUser(CRUDBase[User]):
    """CRUD operations for :class:`User`.

    Username/email lookups are tenant-scoped (DATABASE_DESIGN.md §6):
    ``company_id=None`` resolves within the Super Admin / legacy scope
    (``company_id IS NULL``); a concrete ``company_id`` resolves within that
    company. This mirrors the uniqueness constraints, so each lookup returns
    at most one row.
    """

    def get_by_username(
        self, db: Session, username: str, *, company_id: int | None = None
    ) -> User | None:
        stmt = select(User).where(
            User.username == username, User.deleted_at.is_(None)
        )
        if company_id is None:
            stmt = stmt.where(User.company_id.is_(None))
        else:
            stmt = stmt.where(User.company_id == company_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_email(
        self, db: Session, email: str, *, company_id: int | None = None
    ) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        if company_id is None:
            stmt = stmt.where(User.company_id.is_(None))
        else:
            stmt = stmt.where(User.company_id == company_id)
        return db.execute(stmt).scalar_one_or_none()


user = CRUDUser(User)
