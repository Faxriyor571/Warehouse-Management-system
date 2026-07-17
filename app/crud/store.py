"""Store data-access operations. Every query is scoped to a company."""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.store import Store


class CRUDStore(CRUDBase[Store]):
    """CRUD operations for :class:`Store`, always company-scoped.

    Tenant isolation is enforced here at the data-access layer: a store is
    only ever returned when it belongs to the requesting company, so a query
    can never leak another tenant's stores (DATABASE_DESIGN.md §10).
    """

    def get_for_company(self, db: Session, store_id: int, company_id: int) -> Store | None:
        stmt = select(Store).where(Store.id == store_id, Store.company_id == company_id)
        return db.execute(stmt).scalar_one_or_none()

    def list_for_company(self, db: Session, company_id: int) -> Sequence[Store]:
        stmt = (
            select(Store)
            .where(Store.company_id == company_id)
            .order_by(Store.id.desc())
        )
        return db.execute(stmt).scalars().all()


store = CRUDStore(Store)
