"""User schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.role import RoleSummary


class UserBase(BaseModel):
    """Shared, editable user fields."""

    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)


class UserCreate(UserBase):
    """Payload to create a user."""

    password: str = Field(min_length=6, max_length=128)
    role_id: int
    is_active: bool = True


class UserUpdate(BaseModel):
    """Payload to update a user (admin). All fields optional."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    role_id: int | None = None
    is_active: bool | None = None


class ProfileUpdate(BaseModel):
    """Payload for a user updating their own profile."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)


class PasswordUpdate(BaseModel):
    """Payload for a user changing their own password."""

    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class PasswordReset(BaseModel):
    """Payload for an admin resetting a user's password."""

    new_password: str = Field(min_length=6, max_length=128)


class UserOut(UserBase):
    """User as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_superuser: bool
    # Nullable: users created through the new Companies/Employees flows have
    # no legacy role assignment at all.
    role_id: int | None
    # Legacy RBAC role assignment (being phased out incrementally).
    legacy_role: RoleSummary | None = None
    # Multi-tenant identity (DATABASE_DESIGN.md §3.3). Null until the user
    # has been migrated to / created under the new Companies/Employees flow.
    role: UserRole | None = None
    company_id: int | None = None
    store_id: int | None = None
    last_login_at: datetime | None = None
    created_at: datetime
