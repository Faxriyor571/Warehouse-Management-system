"""Store business logic: creation, updates and deactivation."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.store import store as store_crud
from app.models.enums import UserRole
from app.models.store import Store
from app.models.user import User
from app.schemas.store import StoreCreate, StoreUpdate
from app.utils.exceptions import ConflictError


def create_store(db: Session, company_id: int, data: StoreCreate) -> Store:
    """Create a store owned by ``company_id`` (derived from the token, never client-supplied)."""
    return store_crud.create(
        db,
        {
            "company_id": company_id,
            "name": data.name,
            "address": data.address,
            "phone": data.phone,
            "is_active": True,
        },
    )


def update_store(db: Session, store: Store, data: StoreUpdate) -> Store:
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(store, key, value)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


def _has_active_seller(db: Session, store_id: int) -> bool:
    """Return True if any active, non-deleted Seller is assigned to the store.

    This enforces the real business rule (API_SPECIFICATION.md §3, SRS §4.9),
    not merely the foreign-key relationship: a soft-deleted or deactivated
    former seller does not block deactivation.
    """
    stmt = select(func.count(User.id)).where(
        User.store_id == store_id,
        User.role == UserRole.SELLER,
        User.is_active.is_(True),
        User.deleted_at.is_(None),
    )
    return db.execute(stmt).scalar_one() > 0


def deactivate_store(db: Session, store: Store) -> Store:
    """Deactivate a store (``is_active = false``).

    Deactivation is the only removal path — stores are never hard-deleted
    (DATABASE_DESIGN.md §9). A store with an active Seller still assigned to
    it cannot be deactivated; the Seller must be reassigned or deactivated
    first (API_SPECIFICATION.md §3).
    """
    if _has_active_seller(db, store.id):
        raise ConflictError(
            "Do'konni o'chirib bo'lmaydi: unga biriktirilgan faol sotuvchi bor"
        )
    store.is_active = False
    db.add(store)
    db.commit()
    db.refresh(store)
    return store
