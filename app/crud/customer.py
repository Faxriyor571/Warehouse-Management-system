"""Customer data-access operations."""
from __future__ import annotations

from app.crud.base import CRUDBase
from app.models.customer import Customer


class CRUDCustomer(CRUDBase[Customer]):
    """CRUD operations for :class:`Customer`."""


customer = CRUDCustomer(Customer)
