"""Employee business logic (API_SPECIFICATION.md §4, extended for the ERP
role redesign's job-function split).

Employees are company-scoped users with ``role = SELLER`` and one
``employee_role`` job function (Cashier/Warehouse/Accountant). Only a Cashier
has a mandatory store assignment — Warehouse Employee and Accountant are
company-wide, mirroring the CEO's own scope (a Transfer inherently spans two
stores; an Accountant's financial view spans the whole company). Every
operation here is invoked by a CEO for their own company; the ``company_id``
is always supplied by the caller from the token, never by the client.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import security
from app.crud.store import store as store_crud
from app.crud.user import user as user_crud
from app.models.enums import EmployeeRole, UserRole
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError


def store_name_for(db: Session, company_id: int, store_id: int | None) -> str | None:
    """Return the name of a store within the company (single indexed lookup).

    Used to build single-employee responses. ``store_id`` is ``None`` for a
    company-wide employee (Warehouse/Accountant), which resolves to ``None``
    directly — no lookup needed.
    """
    if store_id is None:
        return None
    store = store_crud.get_for_company(db, store_id, company_id)
    return store.name if store is not None else None


def create_seller(db: Session, company_id: int, data: EmployeeCreate) -> tuple[User, str | None]:
    """Create an employee in the company with the given job function.

    A Cashier requires a valid ``store_id`` in the company; a Warehouse
    Employee or Accountant is company-wide — any ``store_id`` supplied for
    them is ignored (not an error, since a CEO reusing the same form for every
    job function is a reasonable client to support).
    """
    store_id: int | None = None
    store_name: str | None = None
    if data.employee_role == EmployeeRole.CASHIER:
        if data.store_id is None:
            raise ValidationError("store_id majburiy (Kassir/Sotuvchi uchun)")
        store = store_crud.get_for_company(db, data.store_id, company_id)
        if store is None:
            raise NotFoundError(f"Do'kon (id={data.store_id}) ushbu kompaniyada topilmadi")
        store_id, store_name = store.id, store.name

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
        employee_role=data.employee_role,
        company_id=company_id,
        store_id=store_id,
        is_active=True,
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller, store_name


def update_seller(
    db: Session, seller: User, company_id: int, data: EmployeeUpdate
) -> tuple[User, str | None]:
    """Update an employee. Store/job-function reassignment takes effect immediately."""
    payload = data.model_dump(exclude_unset=True)

    effective_role = payload.get("employee_role", seller.employee_role)
    if "employee_role" in payload and payload["employee_role"] is None:
        raise ValidationError("employee_role null bo'lishi mumkin emas")

    if "store_id" in payload:
        # Omitted store_id is absent from the dump (no change); an explicit
        # null is only valid for a company-wide job function — a Cashier must
        # always have a store (API_SPECIFICATION.md §4).
        if payload["store_id"] is None:
            if effective_role == EmployeeRole.CASHIER:
                raise ValidationError("store_id null bo'lishi mumkin emas (do'kon bekor qilinmaydi)")
            seller.store_id = None
        else:
            store = store_crud.get_for_company(db, payload["store_id"], company_id)
            if store is None:
                raise NotFoundError(
                    f"Do'kon (id={payload['store_id']}) ushbu kompaniyada topilmadi"
                )
            seller.store_id = store.id
    elif effective_role == EmployeeRole.CASHIER and seller.store_id is None:
        # Switching an existing company-wide employee to Cashier without also
        # supplying a store would otherwise leave them store-less.
        raise ValidationError("store_id majburiy (Kassir/Sotuvchi uchun)")

    if payload.get("email"):
        existing = user_crud.get_by_email(db, payload["email"], company_id=company_id)
        if existing is not None and existing.id != seller.id:
            raise ConflictError(f"'{payload['email']}' email allaqachon band")

    for key in ("full_name", "email", "phone", "employee_role"):
        if key in payload and payload[key] is not None:
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
