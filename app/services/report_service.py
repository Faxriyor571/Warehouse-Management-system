"""Reporting logic (API_SPECIFICATION.md §14 — sales, inventory, debts, expenses).

Read-only aggregation, company/store scoped. Reuses the Dashboard scope helper
(``dashboard_service._scope_filters``) and the store-stock CRUD so tenant
isolation and the store-stock listing are not re-implemented here.
"""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.store_stock import store_stock as store_stock_crud
from app.models.customer import Customer
from app.models.debt import Debt
from app.models.enums import DebtStatus
from app.models.expense import Expense
from app.models.stock_out import StockOut
from app.schemas.report import (
    ChartPoint,
    DebtByCustomer,
    DebtByStatus,
    DebtReport,
    ExpenseByType,
    ExpenseReport,
    InventoryReport,
    InventoryReportRow,
    PaymentStatusBucket,
    SalesReport,
)
from app.services.dashboard_service import _scope_filters
from app.utils.pagination import MAX_PAGE_SIZE, PageParams

_ZERO = Decimal("0")


def _dec(value) -> Decimal:
    return Decimal(value) if value is not None else _ZERO


def sales_report(
    db: Session,
    *,
    company_id: int | None,
    store_id: int | None,
    date_from: date_type | None,
    date_to: date_type | None,
) -> SalesReport:
    scope = _scope_filters(StockOut, company_id, store_id)
    if date_from is not None:
        scope.append(func.date(StockOut.date) >= date_from)
    if date_to is not None:
        scope.append(func.date(StockOut.date) <= date_to)

    total_revenue, total_count = db.execute(
        select(func.coalesce(func.sum(StockOut.total_amount), 0), func.count(StockOut.id)).where(*scope)
    ).one()

    by_payment_status = [
        PaymentStatusBucket(status=row.status.value, count=row.cnt, revenue=_dec(row.rev))
        for row in db.execute(
            select(
                StockOut.payment_status.label("status"),
                func.count(StockOut.id).label("cnt"),
                func.coalesce(func.sum(StockOut.total_amount), 0).label("rev"),
            )
            .where(*scope)
            .group_by(StockOut.payment_status)
        ).all()
    ]

    by_day = [
        ChartPoint(label=str(row.d), value=_dec(row.total))
        for row in db.execute(
            select(
                func.date(StockOut.date).label("d"),
                func.coalesce(func.sum(StockOut.total_amount), 0).label("total"),
            )
            .where(*scope)
            .group_by(func.date(StockOut.date))
            .order_by(func.date(StockOut.date).asc())
        ).all()
    ]

    return SalesReport(
        total_revenue=_dec(total_revenue),
        total_count=int(total_count or 0),
        by_payment_status=by_payment_status,
        by_day=by_day,
    )


def inventory_report(db: Session, *, company_id: int | None, store_id: int | None) -> InventoryReport:
    # store_stock is a tenant model; the legacy (NULL-company) scope has no
    # store rows, so its report is empty (its stock lives in product.quantity).
    if company_id is None:
        return InventoryReport(rows=[], count=0)

    params = PageParams(page=1, page_size=MAX_PAGE_SIZE)
    if store_id is not None:
        rows, count = store_stock_crud.list_for_store(db, store_id, page_params=params)
    else:
        rows, count = store_stock_crud.list_company_wide(db, company_id, page_params=params)

    return InventoryReport(
        rows=[
            InventoryReportRow(product_id=r.product_id, name=r.product_name, sku=r.sku, quantity=r.quantity)
            for r in rows
        ],
        count=count,
    )


def debt_report(db: Session, *, company_id: int | None, store_id: int | None) -> DebtReport:
    scope = _scope_filters(Debt, company_id, store_id)
    scope.append(Debt.remaining_amount > 0)  # outstanding only

    by_customer = [
        DebtByCustomer(customer_id=row.id, full_name=row.full_name, remaining=_dec(row.rem))
        for row in db.execute(
            select(
                Customer.id,
                Customer.full_name,
                func.coalesce(func.sum(Debt.remaining_amount), 0).label("rem"),
            )
            .join(Debt, Debt.customer_id == Customer.id)
            .where(*scope)
            .group_by(Customer.id, Customer.full_name)
            .order_by(func.sum(Debt.remaining_amount).desc())
        ).all()
    ]

    by_status = [
        DebtByStatus(status=row.status.value, count=row.cnt, remaining=_dec(row.rem))
        for row in db.execute(
            select(
                Debt.status.label("status"),
                func.count(Debt.id).label("cnt"),
                func.coalesce(func.sum(Debt.remaining_amount), 0).label("rem"),
            )
            .where(*scope, Debt.status.in_((DebtStatus.ACTIVE, DebtStatus.OVERDUE)))
            .group_by(Debt.status)
        ).all()
    ]

    total_remaining = _dec(
        db.execute(select(func.coalesce(func.sum(Debt.remaining_amount), 0)).where(*scope)).scalar()
    )
    return DebtReport(by_customer=by_customer, by_status=by_status, total_remaining=total_remaining)


def expense_report(db: Session, *, company_id: int | None, store_id: int | None) -> ExpenseReport:
    scope = _scope_filters(Expense, company_id, store_id)

    by_type = [
        ExpenseByType(expense_type=row.et.value, total=_dec(row.total), count=row.cnt)
        for row in db.execute(
            select(
                Expense.expense_type.label("et"),
                func.coalesce(func.sum(Expense.amount), 0).label("total"),
                func.count(Expense.id).label("cnt"),
            )
            .where(*scope)
            .group_by(Expense.expense_type)
        ).all()
    ]

    by_date = [
        ChartPoint(label=str(row.d), value=_dec(row.total))
        for row in db.execute(
            select(
                Expense.date.label("d"),
                func.coalesce(func.sum(Expense.amount), 0).label("total"),
            )
            .where(*scope)
            .group_by(Expense.date)
            .order_by(Expense.date.asc())
        ).all()
    ]

    total = _dec(db.execute(select(func.coalesce(func.sum(Expense.amount), 0)).where(*scope)).scalar())
    return ExpenseReport(by_type=by_type, by_date=by_date, total=total)
