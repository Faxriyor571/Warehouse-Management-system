"""Unit-of-measurement schemas."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UnitBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    short_name: str = Field(min_length=1, max_length=20)
    conversion_factor: Decimal | None = Field(default=None, ge=0)
    is_active: bool = True


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    short_name: str | None = Field(default=None, min_length=1, max_length=20)
    conversion_factor: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class UnitOut(UnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
