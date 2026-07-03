"""Role schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.permission import PermissionOut


class RoleBase(BaseModel):
    """Shared role fields."""

    name: str = Field(min_length=2, max_length=50)
    description: str | None = None


class RoleCreate(RoleBase):
    """Payload to create a role, optionally with permission codes."""

    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Payload to update a role. All fields optional."""

    name: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = None
    permission_codes: list[str] | None = None


class RoleOut(RoleBase):
    """Role as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_system: bool
    permissions: list[PermissionOut] = Field(default_factory=list)


class RoleSummary(BaseModel):
    """Lightweight role representation for embedding in other responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
