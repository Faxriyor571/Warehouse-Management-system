"""User data-access operations."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Row, func, or_, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.enums import UserRole
from app.models.store import Store
from app.models.user import User
from app.utils.pagination import PageParams


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

    # ------------------------------------------------------------------
    # Sellers (Employees module) — always company-scoped
    # ------------------------------------------------------------------
    def get_seller_for_company(
        self, db: Session, user_id: int, company_id: int
    ) -> User | None:
        """Return a single, non-deleted Seller belonging to the company."""
        stmt = select(User).where(
            User.id == user_id,
            User.company_id == company_id,
            User.role == UserRole.SELLER,
            User.deleted_at.is_(None),
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_sellers_for_company(
        self,
        db: Session,
        company_id: int,
        *,
        page_params: PageParams,
        search: str | None = None,
    ) -> tuple[Sequence[Row[Any]], int]:
        """Return a page of the company's Sellers joined with their store name.

        The assigned store name is fetched in the same query via a join, so a
        page of Sellers costs one query regardless of how many stores the
        company has (no per-row store lookups, no loading all stores). An
        outer join (not inner) so a company-wide employee (Warehouse/
        Accountant, ``store_id IS NULL``) still appears, with ``store_name``
        resolving to ``None``.
        """
        base = (
            select(User, Store.name.label("store_name"))
            .outerjoin(Store, User.store_id == Store.id)
            .where(
                User.company_id == company_id,
                User.role == UserRole.SELLER,
                User.deleted_at.is_(None),
            )
        )
        if search:
            like = f"%{search.strip()}%"
            base = base.where(
                or_(User.username.ilike(like), User.full_name.ilike(like))
            )

        count_stmt = select(func.count()).select_from(base.order_by(None).subquery())
        total = db.execute(count_stmt).scalar_one()

        rows = db.execute(
            base.order_by(User.id.desc())
            .offset(page_params.offset)
            .limit(page_params.limit)
        ).all()
        return rows, total


user = CRUDUser(User)
