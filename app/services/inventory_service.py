"""Inventory service — the single write primitive for on-hand stock.

Every quantity change flows through :func:`apply_movement`, which updates the
maintained ``store_stock`` balance and appends an immutable ``stock_movements``
ledger row in the same unit of work. This is the only place stock is mutated,
so the balance and the ledger can never disagree.

The migrated Stock In / Sales / Sale-Return writers (later phases) will call
this inside their own document transaction (``commit=False``); it is also used
directly by the Inventory tests to seed stock.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.stock_movement import stock_movement as stock_movement_crud
from app.crud.store_stock import store_stock as store_stock_crud
from app.models.enums import MovementType
from app.models.stock_movement import StockMovement
from app.models.store_stock import StoreStock
from app.utils.exceptions import InsufficientStockError


def apply_movement(
    db: Session,
    *,
    company_id: int,
    store_id: int,
    product_id: int,
    movement_type: MovementType,
    quantity_delta: Decimal,
    reference_type: str,
    created_by_id: int,
    reference_id: int | None = None,
    allow_negative: bool = False,
    commit: bool = False,
) -> tuple[StoreStock, StockMovement]:
    """Apply one signed quantity change to a ``(store, product)`` balance.

    Creates the ``store_stock`` row on first movement. A change that would take
    the balance below zero is rejected with ``InsufficientStockError`` unless
    ``allow_negative`` is set (e.g. for a corrective adjustment).
    """
    row = store_stock_crud.get(db, store_id, product_id)
    if row is None:
        row = StoreStock(store_id=store_id, product_id=product_id, quantity=Decimal("0"))
        db.add(row)
        db.flush()

    new_quantity = row.quantity + quantity_delta
    if new_quantity < 0 and not allow_negative:
        raise InsufficientStockError(
            f"Omborda yetarli mahsulot yo'q (mavjud: {row.quantity}, "
            f"o'zgarish: {quantity_delta})"
        )
    row.quantity = new_quantity
    db.add(row)

    movement = StockMovement(
        company_id=company_id,
        store_id=store_id,
        product_id=product_id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by_id=created_by_id,
    )
    db.add(movement)

    if commit:
        db.commit()
        db.refresh(row)
        db.refresh(movement)
    else:
        db.flush()
    return row, movement


def reconcile(db: Session, store_id: int, product_id: int) -> bool:
    """Return True if the maintained balance equals the sum of ledger deltas.

    Powers the integrity guarantee in DATABASE_DESIGN.md §11 and is asserted by
    the Inventory tests.
    """
    row = store_stock_crud.get(db, store_id, product_id)
    balance = row.quantity if row is not None else Decimal("0")
    ledger = Decimal(str(stock_movement_crud.sum_delta(db, store_id, product_id)))
    return balance == ledger
