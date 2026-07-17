"""Employee schemas (API_SPECIFICATION.md §4, extended for the ERP role
redesign's job-function split).

This module manages employees only (``role=SELLER`` + an ``employee_role``
job function); the CEO is created at company onboarding.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import EmployeeRole, UserRole


class EmployeeCreate(BaseModel):
    """Payload to create an employee. ``company_id`` is derived from the token.

    ``store_id`` is required only for a Cashier (confined to one store, same
    as the original Seller model); it's optional — and ignored if given — for
    a company-wide job function (Warehouse Employee, Accountant), enforced in
    ``employee_service.create_seller``, not schema validation, since the rule
    depends on ``employee_role``.
    """

    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=6, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    employee_role: EmployeeRole = EmployeeRole.CASHIER
    store_id: int | None = None


class EmployeeUpdate(BaseModel):
    """Payload to update an employee. Omitted fields are left unchanged.

    ``store_id`` may be reassigned to another store in the company, but for a
    Cashier it may never be cleared — a Cashier must always have a store.
    Omitting the field means "no change"; explicitly sending ``null`` for a
    Cashier is rejected (422, enforced in the service). A Warehouse Employee/
    Accountant may freely set or clear ``store_id`` (company-wide either way).
    ``model_dump(exclude_unset=True)`` distinguishes an omitted ``store_id``
    (absent from the dump) from an explicit ``null`` (present with value
    ``None``).
    """

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    employee_role: EmployeeRole | None = None
    store_id: int | None = None


class EmployeeOut(BaseModel):
    """Employee as returned by the API, with the assigned store's name."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    role: UserRole
    employee_role: EmployeeRole
    store_id: int | None = None
    store_name: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class EmployeePasswordReset(BaseModel):
    """Payload for a CEO resetting a Seller's password."""

    new_password: str = Field(min_length=6, max_length=128)
