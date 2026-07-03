"""Stock-in data-access operations."""
from __future__ import annotations

from app.crud.base import CRUDBase
from app.models.stock_in import StockIn


class CRUDStockIn(CRUDBase[StockIn]):
    """CRUD operations for :class:`StockIn`."""


stock_in = CRUDStockIn(StockIn)
