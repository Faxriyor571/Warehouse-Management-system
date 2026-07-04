"""Debt (Qarz) business logic: creation, repayments and status upkeep."""
from __future__ import annotations

from datetime import date as date_type, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.crud.customer import customer as customer_crud
from app.crud.debt import debt as debt_crud
from app.crud.payment_method import payment_method as pm_crud
from app.models.debt import Debt, DebtPayment
from app.models.enums import AuditAction, DebtStatus, PaymentStatus
from app.schemas.debt import DebtCreate, DebtPaymentCreate
from app.services import audit_service
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
    if pm_crud.get(db, data.payment_method_id) is None:
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


def refresh_overdue(db: Session) -> int:
    """Mark active debts whose due date has passed as overdue. Returns count."""
    today = datetime.now(timezone.utc).date()
    updated = 0
    for debt in debt_crud.get_all(db):
        if (
            debt.status == DebtStatus.ACTIVE
            and debt.remaining_amount > 0
            and debt.due_date is not None
            and debt.due_date < today
        ):
            debt.status = DebtStatus.OVERDUE
            db.add(debt)
            updated += 1
    if updated:
        db.commit()
    return updated


def _status_for_due(due: date_type | None, *, remaining: Decimal) -> DebtStatus:
    if remaining <= 0:
        return DebtStatus.PAID
    if due is not None and due < datetime.now(timezone.utc).date():
        return DebtStatus.OVERDUE
    return DebtStatus.ACTIVE
