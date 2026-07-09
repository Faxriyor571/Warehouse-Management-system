"""Expense business logic (API_SPECIFICATION.md §12).

A single immutable row per call — no inventory effect, no reference number
(not part of DATABASE_DESIGN.md §3.22).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import AuditAction
from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate
from app.services import audit_service
from app.utils.business_time import business_today


def create_expense(
    db: Session,
    data: ExpenseCreate,
    *,
    company_id: int | None,
    store_id: int | None,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Expense:
    expense = Expense(
        company_id=company_id,
        store_id=store_id,
        created_by_id=user_id,
        expense_type=data.expense_type,
        amount=data.amount,
        description=data.description,
        # Business-local (UTC+5) today when not explicitly supplied — the
        # column's server_default is func.current_date(), which runs in the
        # DB session's (UTC) timezone and would misdate expenses recorded
        # between local midnight and 05:00. See app.utils.business_time.
        date=data.date if data.date is not None else business_today(),
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    audit_service.log_action(
        db,
        action=AuditAction.EXPENSE,
        user_id=user_id,
        entity_type="expense",
        entity_id=expense.id,
        description=f"Xarajat qo'shildi: {data.expense_type.value}, summa {data.amount}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return expense
