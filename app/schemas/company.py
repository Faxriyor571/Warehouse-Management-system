"""Company schemas (API_SPECIFICATION.md §2)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import CompanyStatus


class CeoCreate(BaseModel):
    """CEO account created alongside a new company."""

    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=6, max_length=128)
    email: EmailStr | None = None


class CompanyCreate(BaseModel):
    """Payload to onboard a new company."""

    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=30)
    ceo: CeoCreate


class CompanyUpdate(BaseModel):
    """Payload to update a company. ``slug`` is immutable after creation."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=30)


class CompanyNameUpdate(BaseModel):
    """Settings page payload: a CEO renaming their own company. Deliberately
    narrower than CompanyUpdate (name required, no email/phone) — this is
    the only company field Settings exposes."""

    name: str = Field(min_length=2, max_length=200)


class CompanyOut(BaseModel):
    """Company as returned by the API. No business data (SRS §3.1)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    status: CompanyStatus
    contact_email: str | None = None
    contact_phone: str | None = None
    created_at: datetime
    updated_at: datetime


class CeoSummary(BaseModel):
    """Lightweight CEO representation returned on company creation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None = None


class CompanyCreateResponse(BaseModel):
    """Response for company onboarding: the company plus its new CEO."""

    company: CompanyOut
    ceo: CeoSummary


class SupportSessionToken(BaseModel):
    """Response for a System Owner starting a support session into a company.

    Access-token-only, deliberately: see
    app.services.company_service.start_support_session for why a support
    session never gets a refresh token.
    """

    access_token: str
    token_type: str = "bearer"
    company: CompanyOut
