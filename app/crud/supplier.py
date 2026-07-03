"""Supplier data-access operations."""
from __future__ import annotations

from app.crud.base import CRUDBase
from app.models.supplier import Supplier


class CRUDSupplier(CRUDBase[Supplier]):
    """CRUD operations for :class:`Supplier`."""


supplier = CRUDSupplier(Supplier)
