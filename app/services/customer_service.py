"""Customer-related aggregation: debt summary and purchase history."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.debt import Debt
from app.models.enums import DebtStatus
from app.models.stock_out import StockOut
from app.schemas.customer import (
    CustomerDebtSummary,
    PurchaseHistoryItem,
)

_ZERO = Decimal("0")


def get_debt_summary(db: Session, customer_id: int) -> CustomerDebtSummary:
    """Aggregate a customer's debts."""
    totals = db.execute(
        select(
            func.coalesce(func.sum(Debt.amount), 0),
            func.coalesce(func.sum(Debt.paid_amount), 0),
            func.coalesce(func.sum(Debt.remaining_amount), 0),
        ).where(Debt.customer_id == customer_id)
    ).one()

    active_count = int(
        db.execute(
            select(func.count(Debt.id)).where(
                Debt.customer_id == customer_id,
                Debt.status == DebtStatus.ACTIVE,
                Debt.remaining_amount > 0,
            )
        ).scalar_one()
    )
    overdue_count = int(
        db.execute(
            select(func.count(Debt.id)).where(
                Debt.customer_id == customer_id,
                Debt.status == DebtStatus.OVERDUE,
            )
        ).scalar_one()
    )

    return CustomerDebtSummary(
        total_debt=Decimal(totals[0]),
        total_paid=Decimal(totals[1]),
        remaining=Decimal(totals[2]),
        active_debts=active_count,
        overdue_debts=overdue_count,
    )


def get_purchase_history(
    db: Session, customer_id: int, limit: int = 50
) -> list[PurchaseHistoryItem]:
    """Return a customer's most recent sales."""
    rows = (
        db.execute(
            select(StockOut)
            .where(StockOut.customer_id == customer_id)
            .order_by(StockOut.date.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        PurchaseHistoryItem(
            id=row.id,
            reference=row.reference,
            date=row.date,
            total_amount=row.total_amount,
            paid_amount=row.paid_amount,
            payment_status=row.payment_status.value,
        )
        for row in rows
    ]
