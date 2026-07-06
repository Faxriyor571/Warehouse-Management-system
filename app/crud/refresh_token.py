"""Refresh token data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.refresh_token import RefreshToken


class CRUDRefreshToken(CRUDBase[RefreshToken]):
    """CRUD operations for :class:`RefreshToken`."""

    def get_by_hash(self, db: Session, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return db.execute(stmt).scalar_one_or_none()


refresh_token = CRUDRefreshToken(RefreshToken)
