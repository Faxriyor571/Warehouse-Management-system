"""Reporting logic: sales, purchases, debts, inventory and profit."""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.debt import Debt
from app.models.product import Product
from app.models.stock_in import StockIn
from app.models.stock_out import StockOut, StockOutItem
from app.models.supplier import Supplier
from app.schemas.report import (
    DebtReport,
    DebtReportRow,
    InventoryReport,
    InventoryReportRow,
    ProfitReport,
    PurchaseReport,
    PurchaseReportRow,
    SalesReport,
    SalesReportRow,
)

_ZERO = Decimal("0")


def _apply_date_range(stmt, column, date_from: date_type | None, date_to: date_type | None):
    if date_from is not None:
        stmt = stmt.where(func.date(column) >= date_from)
    if date_to is not None:
        stmt = stmt.where(func.date(column) <= date_to)
    return stmt


def sales_report(db: Session, date_from: date_type | None, date_to: date_type | None) -> SalesReport:
    stmt = (
        select(StockOut, Customer.full_name)
        .join(Customer, StockOut.customer_id == Customer.id, isouter=True)
        .order_by(StockOut.date.desc())
    )
    stmt = _apply_date_range(stmt, StockOut.date, date_from, date_to)

    rows: list[SalesReportRow] = []
    total_amount = _ZERO
    total_paid = _ZERO
    for sale, customer_name in db.execute(stmt).all():
        rows.append(
            SalesReportRow(
                reference=sale.reference,
                date=sale.date.date(),
                customer=customer_name,
                total_amount=sale.total_amount,
                paid_amount=sale.paid_amount,
                payment_status=sale.payment_status.value,
            )
        )
        total_amount += sale.total_amount
        total_paid += sale.paid_amount

    return SalesReport(
        rows=rows, total_amount=total_amount, total_paid=total_paid, count=len(rows)
    )


def purchase_report(db: Session, date_from: date_type | None, date_to: date_type | None) -> PurchaseReport:
    stmt = (
        select(StockIn, Supplier.name)
        .join(Supplier, StockIn.supplier_id == Supplier.id, isouter=True)
        .order_by(StockIn.date.desc())
    )
    stmt = _apply_date_range(stmt, StockIn.date, date_from, date_to)

    rows: list[PurchaseReportRow] = []
    total_amount = _ZERO
    for purchase, supplier_name in db.execute(stmt).all():
        rows.append(
            PurchaseReportRow(
                reference=purchase.reference,
                date=purchase.date.date(),
                supplier=supplier_name,
                total_amount=purchase.total_amount,
            )
        )
        total_amount += purchase.total_amount

    return PurchaseReport(rows=rows, total_amount=total_amount, count=len(rows))


def debt_report(db: Session, only_open: bool = False) -> DebtReport:
    stmt = (
        select(Debt, Customer.full_name, Customer.phone)
        .join(Customer, Debt.customer_id == Customer.id)
        .order_by(Debt.due_date.asc().nulls_last())
    )
    if only_open:
        stmt = stmt.where(Debt.remaining_amount > 0)

    rows: list[DebtReportRow] = []
    total_remaining = _ZERO
    for debt, name, phone in db.execute(stmt).all():
        rows.append(
            DebtReportRow(
                customer=name,
                phone=phone,
                amount=debt.amount,
                paid_amount=debt.paid_amount,
                remaining_amount=debt.remaining_amount,
                status=debt.status.value,
                due_date=debt.due_date,
            )
        )
        total_remaining += debt.remaining_amount

    return DebtReport(rows=rows, total_remaining=total_remaining, count=len(rows))


def inventory_report(db: Session) -> InventoryReport:
    stmt = (
        select(Product)
        .where(Product.deleted_at.is_(None))
        .order_by(Product.name.asc())
    )
    rows: list[InventoryReportRow] = []
    total_value = _ZERO
    for product in db.execute(stmt).scalars().all():
        value = (product.quantity * product.purchase_price).quantize(Decimal("0.01"))
        rows.append(
            InventoryReportRow(
                sku=product.sku,
                name=product.name,
                quantity=product.quantity,
                purchase_price=product.purchase_price,
                sale_price=product.sale_price,
                stock_value=value,
            )
        )
        total_value += value

    return InventoryReport(rows=rows, total_stock_value=total_value, count=len(rows))


def profit_report(db: Session, date_from: date_type | None, date_to: date_type | None) -> ProfitReport:
    stmt = (
        select(
            func.coalesce(func.sum(StockOutItem.subtotal), 0),
            func.coalesce(func.sum(StockOutItem.quantity * Product.purchase_price), 0),
            func.count(func.distinct(StockOut.id)),
        )
        .select_from(StockOutItem)
        .join(StockOut, StockOutItem.stock_out_id == StockOut.id)
        .join(Product, StockOutItem.product_id == Product.id)
    )
    stmt = _apply_date_range(stmt, StockOut.date, date_from, date_to)

    revenue_val, cost_val, count_val = db.execute(stmt).one()
    revenue = Decimal(revenue_val or 0)
    cost = Decimal(cost_val or 0)
    return ProfitReport(
        revenue=revenue,
        cost_of_goods=cost,
        gross_profit=(revenue - cost),
        count=int(count_val or 0),
    )
