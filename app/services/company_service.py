"""Company (tenant) business logic: onboarding and lifecycle management."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import security
from app.crud.company import company as company_crud
from app.crud.user import user as user_crud
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.utils.exceptions import ConflictError


def create_company(db: Session, data: CompanyCreate) -> tuple[Company, User]:
    """Onboard a new company and create its one CEO account, atomically."""
    if company_crud.get_by_slug(db, data.slug) is not None:
        raise ConflictError(f"'{data.slug}' slug allaqachon band")
    if user_crud.get_by_username(db, data.ceo.username) is not None:
        raise ConflictError(f"'{data.ceo.username}' username allaqachon band")

    company = Company(
        name=data.name,
        slug=data.slug,
        status=CompanyStatus.ACTIVE,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
    )
    db.add(company)
    db.flush()  # obtain company.id without committing yet

    ceo = User(
        username=data.ceo.username,
        full_name=data.ceo.full_name,
        email=data.ceo.email,
        hashed_password=security.hash_password(data.ceo.password),
        role_id=None,
        role=UserRole.CEO,
        company_id=company.id,
        store_id=None,
        is_active=True,
    )
    db.add(ceo)
    db.commit()
    db.refresh(company)
    db.refresh(ceo)
    return company, ceo


def update_company(db: Session, company: Company, data: CompanyUpdate) -> Company:
    """Update a company's editable fields. ``slug`` is immutable (API_SPECIFICATION.md §2)."""
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(company, key, value)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def activate_company(db: Session, company: Company) -> Company:
    company.status = CompanyStatus.ACTIVE
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def suspend_company(db: Session, company: Company) -> Company:
    """Suspend a company and revoke every active refresh token for its users.

    Suspension blocks login immediately; revoking sessions also stops
    already-issued access tokens from being refreshed once they expire
    (API_SPECIFICATION.md §2).
    """
    company.status = CompanyStatus.SUSPENDED
    db.add(company)
    db.commit()
    db.refresh(company)

    stmt = (
        select(RefreshToken)
        .join(User, RefreshToken.user_id == User.id)
        .where(User.company_id == company.id, RefreshToken.revoked_at.is_(None))
    )
    now = datetime.now(timezone.utc)
    for token in db.execute(stmt).scalars().all():
        token.revoked_at = now
        db.add(token)
    db.commit()

    return company
