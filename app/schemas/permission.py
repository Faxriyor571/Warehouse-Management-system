"""Permission schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PermissionOut(BaseModel):
    """Permission as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    group: str
    description: str | None = None
