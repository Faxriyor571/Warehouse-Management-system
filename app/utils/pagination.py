"""Pagination helpers shared across list endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


@dataclass(slots=True)
class PageParams:
    """Normalised pagination parameters."""

    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if self.page < 1:
            self.page = DEFAULT_PAGE
        if self.page_size < 1:
            self.page_size = DEFAULT_PAGE_SIZE
        if self.page_size > MAX_PAGE_SIZE:
            self.page_size = MAX_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(slots=True)
class Page(Generic[T]):
    """A page of results together with pagination metadata."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1



def make_meta(total: int, params: PageParams) -> dict[str, int | bool]:
    """Build a serialisable pagination metadata dict for API responses."""
    page = Page(items=[], total=total, page=params.page, page_size=params.page_size)
    return {
        "page": page.page,
        "page_size": page.page_size,
        "total": page.total,
        "total_pages": page.total_pages,
        "has_next": page.has_next,
        "has_prev": page.has_prev,
    }
