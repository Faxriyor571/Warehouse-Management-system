"""Dashboard aggregation logic."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.debt import Debt
from app.models.product import Product
from app.models.stock_in import StockIn
from app.models.stock_out import StockOut, StockOutItem
from app.schemas.dashboard import (
    ChartPoint,
    DashboardStats,
    DebtorBrief,
    LowStockProduct,
    RecentOperation,
    TopProduct,
)

_ZERO = Decimal("0")


def _scalar(db: Session, stmt) -> Decimal:
    value = db.execute(stmt).scalar()
    return Decimal(value) if value is not None else _ZERO


def get_stats(db: Session) -> DashboardStats:
    """Compute all dashboard figures in one call."""
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)

    # --- Today's totals ---
    today_in = _scalar(
        db,
        select(func.coalesce(func.sum(StockIn.total_amount), 0)).where(
            func.date(StockIn.date) == today
        ),
    )
    today_out = _scalar(
        db,
        select(func.coalesce(func.sum(StockOut.total_amount), 0)).where(
            func.date(StockOut.date) == today
        ),
    )
    today_sales_count = int(
        db.execute(
            select(func.count(StockOut.id)).where(func.date(StockOut.date) == today)
        ).scalar_one()
    )

    # --- Today's profit = revenue - cost of goods sold ---
    profit_stmt = (
        select(
            func.coalesce(func.sum(StockOutItem.subtotal), 0)
            - func.coalesce(func.sum(StockOutItem.quantity * Product.purchase_price), 0)
        )
        .select_from(StockOutItem)
        .join(StockOut, StockOutItem.stock_out_id == StockOut.id)
        .join(Product, StockOutItem.product_id == Product.id)
        .where(func.date(StockOut.date) == today)
    )
    today_profit = _scalar(db, profit_stmt)

    # --- Monthly revenue / expense ---
    month_revenue = _scalar(
        db,
        select(func.coalesce(func.sum(StockOut.total_amount), 0)).where(
            func.date(StockOut.date) >= month_start
        ),
    )
    month_expense = _scalar(
        db,
        select(func.coalesce(func.sum(StockIn.total_amount), 0)).where(
            func.date(StockIn.date) >= month_start
        ),
    )

    # --- Debtors ---
    debtors_total = _scalar(
        db,
        select(func.coalesce(func.sum(Debt.remaining_amount), 0)).where(
            Debt.remaining_amount > 0
        ),
    )
    debtors_count = int(
        db.execute(
            select(func.count(func.distinct(Debt.customer_id))).where(
                Debt.remaining_amount > 0
            )
        ).scalar_one()
    )

    # --- Inventory ---
    products_count = int(
        db.execute(
            select(func.count(Product.id)).where(
                Product.deleted_at.is_(None), Product.is_active.is_(True)
            )
        ).scalar_one()
    )
    total_stock_value = _scalar(
        db,
        select(func.coalesce(func.sum(Product.quantity * Product.purchase_price), 0)).where(
            Product.deleted_at.is_(None)
        ),
    )

    # --- Low stock products ---
    low_rows = (
        db.execute(
            select(Product)
            .where(
                Product.deleted_at.is_(None),
                Product.is_active.is_(True),
                Product.quantity <= Product.min_quantity,
            )
            .order_by(Product.quantity.asc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    low_stock_products = [
        LowStockProduct(
            product_id=p.id,
            name=p.name,
            sku=p.sku,
            quantity=p.quantity,
            min_quantity=p.min_quantity,
        )
        for p in low_rows
    ]

    # --- Top products (by revenue, all time) ---
    top_stmt = (
        select(
            Product.id,
            Product.name,
            func.coalesce(func.sum(StockOutItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(StockOutItem.subtotal), 0).label("rev"),
        )
        .join(StockOutItem, StockOutItem.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(StockOutItem.subtotal).desc())
        .limit(5)
    )
    top_products = [
        TopProduct(
            product_id=row.id,
            name=row.name,
            quantity_sold=Decimal(row.qty),
            revenue=Decimal(row.rev),
        )
        for row in db.execute(top_stmt).all()
    ]

    # --- Top debtors ---
    debtor_stmt = (
        select(
            Customer.id,
            Customer.full_name,
            Customer.phone,
            func.coalesce(func.sum(Debt.remaining_amount), 0).label("rem"),
        )
        .join(Debt, Debt.customer_id == Customer.id)
        .where(Debt.remaining_amount > 0)
        .group_by(Customer.id, Customer.full_name, Customer.phone)
        .order_by(func.sum(Debt.remaining_amount).desc())
        .limit(5)
    )
    debtors = [
        DebtorBrief(
            customer_id=row.id,
            full_name=row.full_name,
            phone=row.phone,
            remaining=Decimal(row.rem),
        )
        for row in db.execute(debtor_stmt).all()
    ]

    # --- Recent operations (last 5 in + 5 out, merged) ---
    recent_ins = (
        db.execute(select(StockIn).order_by(StockIn.date.desc()).limit(5)).scalars().all()
    )
    recent_outs = (
        db.execute(select(StockOut).order_by(StockOut.date.desc()).limit(5)).scalars().all()
    )
    recent_operations: list[RecentOperation] = []
    for si in recent_ins:
        recent_operations.append(
            RecentOperation(
                type="stock_in",
                reference=si.reference,
                date=si.date,
                amount=si.total_amount,
                partner=si.supplier.name if si.supplier else None,
            )
        )
    for so in recent_outs:
        recent_operations.append(
            RecentOperation(
                type="stock_out",
                reference=so.reference,
                date=so.date,
                amount=so.total_amount,
                partner=so.customer.full_name if so.customer else None,
            )
        )
    recent_operations.sort(key=lambda op: op.date, reverse=True)
    recent_operations = recent_operations[:10]

    # --- Sales chart (last 7 days) ---
    seven_days_ago = today - timedelta(days=6)
    chart_stmt = (
        select(
            func.date(StockOut.date).label("d"),
            func.coalesce(func.sum(StockOut.total_amount), 0).label("total"),
        )
        .where(func.date(StockOut.date) >= seven_days_ago)
        .group_by(func.date(StockOut.date))
    )
    chart_map: dict[str, Decimal] = {}
    for row in db.execute(chart_stmt).all():
        chart_map[str(row.d)] = Decimal(row.total)
    sales_chart = [
        ChartPoint(
            label=str(seven_days_ago + timedelta(days=i)),
            value=chart_map.get(str(seven_days_ago + timedelta(days=i)), _ZERO),
        )
        for i in range(7)
    ]

    return DashboardStats(
        today_stock_in_total=today_in,
        today_stock_out_total=today_out,
        today_sales_count=today_sales_count,
        today_profit=today_profit,
        month_revenue=month_revenue,
        month_expense=month_expense,
        debtors_count=debtors_count,
        debtors_total=debtors_total,
        products_count=products_count,
        total_stock_value=total_stock_value,
        low_stock_count=len(low_stock_products),
        low_stock_products=low_stock_products,
        top_products=top_products,
        debtors=debtors,
        recent_operations=recent_operations,
        sales_chart=sales_chart,
    )
