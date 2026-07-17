"""Debt (Qarz) business logic: creation, repayments and status upkeep."""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.crud.customer import customer as customer_crud
from app.crud.payment_method import payment_method as pm_crud
from app.models.debt import Debt, DebtPayment
from app.models.enums import AuditAction, DebtStatus, PaymentStatus
from app.schemas.debt import DebtCreate, DebtDueDateUpdate, DebtPaymentCreate
from app.services import audit_service
from app.utils.business_time import business_today
from app.utils.exceptions import NotFoundError, ValidationError

_CENT = Decimal("0.01")


def create_debt(
    db: Session,
    data: DebtCreate,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Debt:
    """Create a standalone debt not tied to a specific sale."""
    if customer_crud.get(db, data.customer_id) is None:
        raise NotFoundError(f"Mijoz (id={data.customer_id}) topilmadi")

    debt = Debt(
        customer_id=data.customer_id,
        created_by_id=user_id,
        amount=data.amount,
        paid_amount=Decimal("0"),
        remaining_amount=data.amount,
        due_date=data.due_date,
        status=_status_for_due(data.due_date, remaining=data.amount),
        note=data.note,
    )
    if data.start_date is not None:
        debt.start_date = data.start_date
    db.add(debt)
    db.commit()
    db.refresh(debt)

    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=user_id,
        entity_type="debt",
        entity_id=debt.id,
        description=f"Yangi qarz yaratildi: mijoz {data.customer_id}, summa {data.amount}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return debt


def add_payment(
    db: Session,
    debt: Debt,
    data: DebtPaymentCreate,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DebtPayment:
    """Record a repayment toward a debt and update balances/status."""
    if debt.status == DebtStatus.PAID or debt.remaining_amount <= 0:
        raise ValidationError("Bu qarz allaqachon to'liq to'langan")
    if pm_crud.get_for_company(db, data.payment_method_id, debt.company_id) is None:
        raise NotFoundError(f"To'lov turi (id={data.payment_method_id}) topilmadi")
    if data.amount > debt.remaining_amount:
        raise ValidationError(
            f"To'lov summasi qoldiqdan katta (qoldiq: {debt.remaining_amount})"
        )

    payment = DebtPayment(
        debt_id=debt.id,
        payment_method_id=data.payment_method_id,
        created_by_id=user_id,
        amount=data.amount,
        note=data.note,
    )
    db.add(payment)

    debt.paid_amount = (debt.paid_amount + data.amount).quantize(_CENT)
    debt.remaining_amount = (debt.amount - debt.paid_amount).quantize(_CENT)
    debt.status = _status_for_due(debt.due_date, remaining=debt.remaining_amount)
    db.add(debt)

    # Keep the linked sale's paid amount / status in sync.
    if debt.stock_out is not None:
        sale = debt.stock_out
        sale.paid_amount = (sale.paid_amount + data.amount).quantize(_CENT)
        if sale.paid_amount >= sale.total_amount:
            sale.payment_status = PaymentStatus.PAID
        elif sale.paid_amount > 0:
            sale.payment_status = PaymentStatus.PARTIAL
        db.add(sale)

    db.commit()
    db.refresh(payment)
    db.refresh(debt)

    audit_service.log_action(
        db,
        action=AuditAction.PAYMENT,
        user_id=user_id,
        entity_type="debt",
        entity_id=debt.id,
        description=f"Qarz to'lovi: {data.amount}, qoldiq {debt.remaining_amount}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return payment


def update_due_date(
    db: Session,
    debt: Debt,
    data: DebtDueDateUpdate,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Debt:
    """Edit a debt's due date and recompute its status (API_SPECIFICATION.md §11)."""
    debt.due_date = data.due_date
    debt.status = _status_for_due(debt.due_date, remaining=debt.remaining_amount)
    db.add(debt)
    db.commit()
    db.refresh(debt)

    audit_service.log_action(
        db,
        action=AuditAction.UPDATE,
        user_id=user_id,
        entity_type="debt",
        entity_id=debt.id,
        description=f"Qarz muddati o'zgartirildi: {debt.due_date}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return debt


def refresh_overdue(db: Session, *, company_id: int | None, store_id: int | None = None) -> int:
    """Flip stale ACTIVE debts whose due date has passed to OVERDUE.

    Nothing re-evaluates a debt's status after creation except a payment or a
    due-date edit, so a debt left untouched past its due date would otherwise
    keep reading ACTIVE indefinitely. Called at the top of the debt list and
    debt report reads (tenant-scoped, single bulk UPDATE) so "overdue" is
    always accurate as of today rather than as of whenever the row was last
    written.
    """
    today = business_today()
    company_filter = Debt.company_id.is_(None) if company_id is None else Debt.company_id == company_id
    stmt = (
        update(Debt)
        .where(
            company_filter,
            Debt.status == DebtStatus.ACTIVE,
            Debt.remaining_amount > 0,
            Debt.due_date.is_not(None),
            Debt.due_date < today,
        )
        .values(status=DebtStatus.OVERDUE)
    )
    if store_id is not None:
        stmt = stmt.where(Debt.store_id == store_id)
    result = db.execute(stmt)
    if result.rowcount:
        db.commit()
    return result.rowcount


def _status_for_due(due: date_type | None, *, remaining: Decimal) -> DebtStatus:
    if remaining <= 0:
        return DebtStatus.PAID
    if due is not None and due < business_today():
        return DebtStatus.OVERDUE
    return DebtStatus.ACTIVE
