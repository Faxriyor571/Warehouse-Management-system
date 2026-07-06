"""Store schemas (API_SPECIFICATION.md §3)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoreCreate(BaseModel):
    """Payload to create a store. ``company_id`` is derived from the token."""

    name: str = Field(min_length=2, max_length=200)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)


class StoreUpdate(BaseModel):
    """Payload to update a store. All fields optional."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)


class StoreOut(BaseModel):
    """Full store representation (CEO view)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    address: str | None = None
    phone: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StoreNameOut(BaseModel):
    """Reduced store representation (Seller list view): id + name only.

    A Seller's only legitimate need to see other stores is to resolve store
    names when browsing cross-store inventory quantities (SRS rule #4); no
    address, phone, or activity status is exposed.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
