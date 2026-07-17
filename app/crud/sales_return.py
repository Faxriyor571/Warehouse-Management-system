"""Sale-return data-access operations."""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.sales_return import SalesReturn, SalesReturnItem


class CRUDSalesReturn(CRUDBase[SalesReturn]):
    """CRUD operations for :class:`SalesReturn`."""

    def list_for_sale(self, db: Session, stock_out_id: int) -> Sequence[SalesReturn]:
        stmt = (
            select(SalesReturn)
            .where(SalesReturn.stock_out_id == stock_out_id)
            .order_by(SalesReturn.id.asc())
        )
        return db.execute(stmt).scalars().all()

    def already_returned_quantity(self, db: Session, stock_out_item_id: int) -> Decimal:
        """Sum of quantities already returned against one original sale line."""
        stmt = select(func.coalesce(func.sum(SalesReturnItem.quantity), 0)).where(
            SalesReturnItem.stock_out_item_id == stock_out_item_id
        )
        return Decimal(str(db.execute(stmt).scalar_one()))


sales_return = CRUDSalesReturn(SalesReturn)
