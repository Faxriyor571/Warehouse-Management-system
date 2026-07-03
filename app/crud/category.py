"""Category data-access operations."""
from __future__ import annotations

from app.crud.base import CRUDBase
from app.models.category import Category


class CRUDCategory(CRUDBase[Category]):
    """CRUD operations for :class:`Category`."""


category = CRUDCategory(Category)
