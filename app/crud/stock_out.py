"""Stock-out data-access operations."""
from __future__ import annotations

from app.crud.base import CRUDBase
from app.models.stock_out import StockOut


class CRUDStockOut(CRUDBase[StockOut]):
    """CRUD operations for :class:`StockOut`."""


stock_out = CRUDStockOut(StockOut)
