"""User data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.user import User


class CRUDUser(CRUDBase[User]):
    """CRUD operations for :class:`User`."""

    def get_by_username(self, db: Session, username: str) -> User | None:
        stmt = select(User).where(
            User.username == username, User.deleted_at.is_(None)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, db: Session, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        return db.execute(stmt).scalar_one_or_none()


user = CRUDUser(User)
