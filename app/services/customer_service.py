"""Customer business logic: creation/update rules, debt summary and purchase
history aggregation, and deactivation (API_SPECIFICATION.md §10)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.customer import customer as customer_crud
from app.models.customer import Customer
from app.models.debt import Debt
from app.models.enums import AuditAction, CustomerType, DebtStatus
from app.models.stock_out import StockOut
from app.schemas.customer import (
    CustomerCreate,
    CustomerDebtSummary,
    CustomerUpdate,
    PurchaseHistoryItem,
)
from app.services import audit_service
from app.utils.exceptions import ConflictError, ValidationError

_ZERO = Decimal("0")


def create_customer(
    db: Session,
    data: CustomerCreate,
    *,
    company_id: int | None,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Customer:
    """Create a customer. ``customer_type`` is required for a tenant actor
    (company_id is not None); the legacy single-tenant flow may omit it.

    ``full_name`` is required for a Legal Entity (and the legacy, type-less
    flow) but optional for an Individual — a walk-in individual buyer gets a
    generated placeholder rather than being forced to have a name on file.
    The ``full_name`` column itself stays ``NOT NULL``; only the caller's
    requirement to supply one is conditional.
    """
    if company_id is not None and data.customer_type is None:
        raise ValidationError("customer_type majburiy (individual yoki legal_entity)")

    full_name = data.full_name.strip() if data.full_name else ""
    if data.customer_type == CustomerType.INDIVIDUAL:
        if not full_name:
            full_name = f"Jismoniy shaxs ({data.phone})" if data.phone else "Jismoniy shaxs"
    else:
        if len(full_name) < 2:
            raise ValidationError("F.I.Sh. kamida 2 belgidan iborat bo'lishi kerak")

    payload = data.model_dump()
    payload["company_id"] = company_id
    payload["full_name"] = full_name
    obj = customer_crud.create(db, payload)

    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=user_id,
        entity_type="customer",
        entity_id=obj.id,
        description=f"Mijoz qo'shildi: {obj.full_name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return obj


def update_customer(
    db: Session,
    obj: Customer,
    data: CustomerUpdate,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Customer:
    updated = customer_crud.update(db, obj, data.model_dump(exclude_unset=True))
    audit_service.log_action(
        db,
        action=AuditAction.UPDATE,
        user_id=user_id,
        entity_type="customer",
        entity_id=updated.id,
        description=f"Mijoz yangilandi: {updated.full_name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return updated


def deactivate_customer(
    db: Session,
    obj: Customer,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Customer:
    """Soft-delete a customer. Blocked (409) while any debt remains
    outstanding (API_SPECIFICATION.md §10)."""
    summary = get_debt_summary(db, obj.id)
    if summary.remaining > 0:
        raise ConflictError(
            "Qoldiq qarzi bor mijozni faolsizlantirib bo'lmaydi: avval qarzni yoping"
        )

    customer_crud.remove(db, obj)
    audit_service.log_action(
        db,
        action=AuditAction.DELETE,
        user_id=user_id,
        entity_type="customer",
        entity_id=obj.id,
        description=f"Mijoz faolsizlantirildi: {obj.full_name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return obj


def get_debt_summary(
    db: Session, customer_id: int, *, store_id: int | None = None
) -> CustomerDebtSummary:
    """Aggregate a customer's debts, optionally filtered to one store (Seller)."""
    filters = [Debt.customer_id == customer_id]
    if store_id is not None:
        filters.append(Debt.store_id == store_id)

    totals = db.execute(
        select(
            func.coalesce(func.sum(Debt.amount), 0),
            func.coalesce(func.sum(Debt.paid_amount), 0),
            func.coalesce(func.sum(Debt.remaining_amount), 0),
        ).where(*filters)
    ).one()

    active_count = int(
        db.execute(
            select(func.count(Debt.id)).where(
                *filters, Debt.status == DebtStatus.ACTIVE, Debt.remaining_amount > 0
            )
        ).scalar_one()
    )
    overdue_count = int(
        db.execute(
            select(func.count(Debt.id)).where(*filters, Debt.status == DebtStatus.OVERDUE)
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
    db: Session, customer_id: int, *, store_id: int | None = None, limit: int = 50
) -> list[PurchaseHistoryItem]:
    """Return a customer's most recent sales, optionally filtered to one
    store (Seller)."""
    filters = [StockOut.customer_id == customer_id]
    if store_id is not None:
        filters.append(StockOut.store_id == store_id)

    rows = (
        db.execute(
            select(StockOut).where(*filters).order_by(StockOut.date.desc()).limit(limit)
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
