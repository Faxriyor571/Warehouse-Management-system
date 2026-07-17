"""Stock-movement (ledger) data-access operations. Always company-scoped."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.models.enums import MovementType
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.utils.pagination import PageParams


class CRUDStockMovement:
    """Read access for the append-only :class:`StockMovement` ledger."""

    def list(
        self,
        db: Session,
        company_id: int,
        *,
        page_params: PageParams,
        store_id: int | None = None,
        product_id: int | None = None,
        movement_type: MovementType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[Sequence[Row[Any]], int]:
        """Rows of ``(StockMovement, created_by_name)`` scoped to the company."""
        base = (
            select(StockMovement, User.full_name.label("created_by"))
            .join(User, StockMovement.created_by_id == User.id)
            .where(StockMovement.company_id == company_id)
        )
        if store_id is not None:
            base = base.where(StockMovement.store_id == store_id)
        if product_id is not None:
            base = base.where(StockMovement.product_id == product_id)
        if movement_type is not None:
            base = base.where(StockMovement.movement_type == movement_type)
        if date_from is not None:
            base = base.where(StockMovement.created_at >= date_from)
        if date_to is not None:
            base = base.where(StockMovement.created_at <= date_to)

        total = db.execute(
            select(func.count()).select_from(base.order_by(None).subquery())
        ).scalar_one()
        rows = db.execute(
            base.order_by(StockMovement.id.desc())
            .offset(page_params.offset)
            .limit(page_params.limit)
        ).all()
        return rows, total

    def sum_delta(self, db: Session, store_id: int, product_id: int) -> Any:
        """Sum of all movement deltas for a ``(store, product)`` — reconciliation."""
        stmt = select(func.coalesce(func.sum(StockMovement.quantity_delta), 0)).where(
            StockMovement.store_id == store_id, StockMovement.product_id == product_id
        )
        return db.execute(stmt).scalar_one()


stock_movement = CRUDStockMovement()
