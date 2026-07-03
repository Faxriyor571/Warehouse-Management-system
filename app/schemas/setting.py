"""Application setting schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SettingUpsert(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str | None = None
    description: str | None = Field(default=None, max_length=255)


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: str | None = None
    description: str | None = None
