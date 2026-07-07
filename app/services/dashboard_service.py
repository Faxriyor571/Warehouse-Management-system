"""Dashboard aggregation logic (API_SPECIFICATION.md §13).

Role-based: a Seller's view is scoped to ``company_id`` + their own
``store_id``; a CEO's (and the legacy admin's) view is scoped to
``company_id`` only (company-wide / NULL-scope-wide). Reuses the existing
Sales, Stock In, Debt and Expense models directly (read-only aggregation, no
new business logic).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.debt import Debt
from app.models.expense import Expense
from app.models.product import Product
from app.models.stock_in import StockIn
from app.models.stock_out import StockOut, StockOutItem
from app.schemas.dashboard import (
    ChartPoint,
    DashboardStats,
    RecentOperation,
    TopDebtor,
    TopProduct,
)

_ZERO = Decimal("0")


def _scope_filters(model, company_id: int | None, store_id: int | None) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    filters.append(model.company_id.is_(None) if company_id is None else model.company_id == company_id)
    if store_id is not None:
        filters.append(model.store_id == store_id)
    return filters


def _scalar(db: Session, stmt) -> Decimal:
    value = db.execute(stmt).scalar()
    return Decimal(value) if value is not None else _ZERO


def get_stats(db: Session, *, company_id: int | None, store_id: int | None) -> DashboardStats:
    """Compute all dashboard figures for one company (or one store within it)."""
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)

    so_scope = _scope_filters(StockOut, company_id, store_id)
    si_scope = _scope_filters(StockIn, company_id, store_id)
    debt_scope = _scope_filters(Debt, company_id, store_id)
    exp_scope = _scope_filters(Expense, company_id, store_id)

    # --- Today's sales ---
    today_sales_total = _scalar(
        db,
        select(func.coalesce(func.sum(StockOut.total_amount), 0)).where(
            *so_scope, func.date(StockOut.date) == today
        ),
    )
    today_sales_count = int(
        db.execute(
            select(func.count(StockOut.id)).where(*so_scope, func.date(StockOut.date) == today)
        ).scalar_one()
    )

    # --- Monthly revenue / expenses ---
    month_revenue = _scalar(
        db,
        select(func.coalesce(func.sum(StockOut.total_amount), 0)).where(
            *so_scope, func.date(StockOut.date) >= month_start
        ),
    )
    month_expenses = _scalar(
        db,
        select(func.coalesce(func.sum(Expense.amount), 0)).where(*exp_scope, Expense.date >= month_start),
    )

    # --- Debtors ---
    debtors_total = _scalar(
        db, select(func.coalesce(func.sum(Debt.remaining_amount), 0)).where(*debt_scope, Debt.remaining_amount > 0)
    )
    debtors_count = int(
        db.execute(
            select(func.count(func.distinct(Debt.customer_id))).where(*debt_scope, Debt.remaining_amount > 0)
        ).scalar_one()
    )

    # --- Top products (by revenue, scoped) ---
    top_stmt = (
        select(
            Product.id,
            Product.name,
            func.coalesce(func.sum(StockOutItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(StockOutItem.subtotal), 0).label("rev"),
        )
        .join(StockOutItem, StockOutItem.product_id == Product.id)
        .join(StockOut, StockOutItem.stock_out_id == StockOut.id)
        .where(*so_scope)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(StockOutItem.subtotal).desc())
        .limit(5)
    )
    top_products = [
        TopProduct(product_id=row.id, name=row.name, quantity_sold=Decimal(row.qty), revenue=Decimal(row.rev))
        for row in db.execute(top_stmt).all()
    ]

    # --- Top debtors (scoped) ---
    debtor_stmt = (
        select(
            Customer.id,
            Customer.full_name,
            func.coalesce(func.sum(Debt.remaining_amount), 0).label("rem"),
        )
        .join(Debt, Debt.customer_id == Customer.id)
        .where(*debt_scope, Debt.remaining_amount > 0)
        .group_by(Customer.id, Customer.full_name)
        .order_by(func.sum(Debt.remaining_amount).desc())
        .limit(5)
    )
    top_debtors = [
        TopDebtor(customer_id=row.id, full_name=row.full_name, remaining=Decimal(row.rem))
        for row in db.execute(debtor_stmt).all()
    ]

    # --- Recent operations (last 5 sales + 5 stock-ins, merged, scoped) ---
    recent_ins = db.execute(select(StockIn).where(*si_scope).order_by(StockIn.date.desc()).limit(5)).scalars().all()
    recent_outs = db.execute(select(StockOut).where(*so_scope).order_by(StockOut.date.desc()).limit(5)).scalars().all()
    recent_operations = [
        RecentOperation(type="stock_in", reference=si.reference, date=si.date, amount=si.total_amount)
        for si in recent_ins
    ] + [
        RecentOperation(type="sale", reference=so.reference, date=so.date, amount=so.total_amount)
        for so in recent_outs
    ]
    recent_operations.sort(key=lambda op: op.date, reverse=True)
    recent_operations = recent_operations[:10]

    # --- Sales chart (last 7 days, scoped) ---
    seven_days_ago = today - timedelta(days=6)
    chart_stmt = (
        select(func.date(StockOut.date).label("d"), func.coalesce(func.sum(StockOut.total_amount), 0).label("total"))
        .where(*so_scope, func.date(StockOut.date) >= seven_days_ago)
        .group_by(func.date(StockOut.date))
    )
    chart_map: dict[str, Decimal] = {str(row.d): Decimal(row.total) for row in db.execute(chart_stmt).all()}
    sales_chart = [
        ChartPoint(label=str(d), value=chart_map.get(str(d), _ZERO))
        for d in (seven_days_ago + timedelta(days=i) for i in range(7))
    ]

    return DashboardStats(
        scope="store" if store_id is not None else "company",
        today_sales_total=today_sales_total,
        today_sales_count=today_sales_count,
        month_revenue=month_revenue,
        month_expenses=month_expenses,
        debtors_count=debtors_count,
        debtors_total=debtors_total,
        top_products=top_products,
        top_debtors=top_debtors,
        recent_operations=recent_operations,
        sales_chart=sales_chart,
    )
