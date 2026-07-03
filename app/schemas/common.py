"""Common/shared Pydantic schemas."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Message(BaseModel):
    """A simple message response."""

    detail: str


class PageMeta(BaseModel):
    """Pagination metadata attached to list responses."""

    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """A generic paginated list response."""

    items: list[T]
    meta: PageMeta


class ListQuery(BaseModel):
    """Common query parameters for list endpoints."""

    search: str | None = Field(default=None, description="Qidiruv matni")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
