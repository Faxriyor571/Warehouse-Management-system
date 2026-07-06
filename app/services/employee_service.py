"""Employee (Seller) business logic (API_SPECIFICATION.md §4).

Sellers are company-scoped users with ``role = SELLER`` and a mandatory store
assignment. Every operation here is invoked by a CEO for their own company;
the ``company_id`` is always supplied by the caller from the token, never by
the client.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import security
from app.crud.store import store as store_crud
from app.crud.user import user as user_crud
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError


def store_name_for(db: Session, company_id: int, store_id: int) -> str:
    """Return the name of a store within the company (single indexed lookup).

    Used to build single-Seller responses. A valid Seller always references an
    existing store in its company (enforced on create/update), so this resolves
    to a name; the fallback keeps the response well-formed if that invariant is
    ever violated by out-of-band data changes.
    """
    store = store_crud.get_for_company(db, store_id, company_id)
    return store.name if store is not None else ""


def create_seller(db: Session, company_id: int, data: EmployeeCreate) -> tuple[User, str]:
    """Create a Seller in the company with the given store assignment."""
    store = store_crud.get_for_company(db, data.store_id, company_id)
    if store is None:
        raise NotFoundError(f"Do'kon (id={data.store_id}) ushbu kompaniyada topilmadi")

    if user_crud.get_by_username(db, data.username, company_id=company_id) is not None:
        raise ConflictError(f"'{data.username}' username allaqachon band")
    if data.email and user_crud.get_by_email(db, data.email, company_id=company_id) is not None:
        raise ConflictError(f"'{data.email}' email allaqachon band")

    seller = User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        hashed_password=security.hash_password(data.password),
        role_id=None,
        role=UserRole.SELLER,
        company_id=company_id,
        store_id=store.id,
        is_active=True,
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller, store.name


def update_seller(
    db: Session, seller: User, company_id: int, data: EmployeeUpdate
) -> tuple[User, str]:
    """Update a Seller. Store reassignment takes effect immediately."""
    payload = data.model_dump(exclude_unset=True)

    if "store_id" in payload:
        # Omitted store_id is absent from the dump (no change); an explicit
        # null is present as None and is rejected — a Seller must always have
        # a store (API_SPECIFICATION.md §4).
        if payload["store_id"] is None:
            raise ValidationError("store_id null bo'lishi mumkin emas (do'kon bekor qilinmaydi)")
        store = store_crud.get_for_company(db, payload["store_id"], company_id)
        if store is None:
            raise NotFoundError(
                f"Do'kon (id={payload['store_id']}) ushbu kompaniyada topilmadi"
            )
        seller.store_id = store.id

    if payload.get("email"):
        existing = user_crud.get_by_email(db, payload["email"], company_id=company_id)
        if existing is not None and existing.id != seller.id:
            raise ConflictError(f"'{payload['email']}' email allaqachon band")

    for key in ("full_name", "email", "phone"):
        if key in payload:
            setattr(seller, key, payload[key])

    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller, store_name_for(db, company_id, seller.store_id)


def set_seller_active(
    db: Session, seller: User, company_id: int, is_active: bool
) -> tuple[User, str]:
    """Activate or deactivate a Seller.

    Deactivation blocks both login and refresh (both check ``is_active``); it
    does not touch the Seller's historical records. No separate token
    revocation is performed — the ``is_active`` check already prevents session
    continuation on refresh.
    """
    seller.is_active = is_active
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller, store_name_for(db, company_id, seller.store_id)


def reset_seller_password(db: Session, seller: User, new_password: str) -> None:
    """Reset a Seller's password (CEO action, no old-password check).

    Note on session revocation: API_SPECIFICATION.md §4 only *recommends*
    (does not require) revoking the Seller's refresh tokens on reset, and
    DATABASE_DESIGN.md §12 lists forced revocation only for company suspension
    and user deactivation — not password reset. Per scope discipline we do not
    add that behavior here; existing sessions remain valid until they expire or
    are logged out. Promote it to a confirmed requirement first if it is wanted.
    """
    seller.hashed_password = security.hash_password(new_password)
    db.add(seller)
    db.commit()
