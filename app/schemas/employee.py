"""Employee (Seller) schemas (API_SPECIFICATION.md §4).

This module manages Sellers only; the CEO is created at company onboarding.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class EmployeeCreate(BaseModel):
    """Payload to create a Seller. ``company_id`` is derived from the token."""

    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=6, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    # Required: a Seller is always assigned to exactly one store
    # (DATABASE_DESIGN.md §12). A missing store_id is a 422.
    store_id: int


class EmployeeUpdate(BaseModel):
    """Payload to update a Seller. Omitted fields are left unchanged.

    ``store_id`` may be reassigned to another store in the company, but it may
    never be cleared — a Seller must always have a store. Omitting the field
    means "no change"; explicitly sending ``null`` is rejected (422, enforced
    in the service) rather than silently overloaded with hidden behavior.
    ``model_dump(exclude_unset=True)`` distinguishes the two cases: an omitted
    ``store_id`` is absent from the dump, while an explicit ``null`` is present
    with value ``None``.
    """

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    store_id: int | None = None


class EmployeeOut(BaseModel):
    """Seller as returned by the API, with the assigned store's name."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    role: UserRole
    store_id: int
    store_name: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class EmployeePasswordReset(BaseModel):
    """Payload for a CEO resetting a Seller's password."""

    new_password: str = Field(min_length=6, max_length=128)
