"""Dashboard schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TopProduct(BaseModel):
    product_id: int
    name: str
    quantity_sold: Decimal
    revenue: Decimal


class LowStockProduct(BaseModel):
    product_id: int
    name: str
    sku: str
    quantity: Decimal
    min_quantity: Decimal


class RecentOperation(BaseModel):
    type: str  # "stock_in" | "stock_out"
    reference: str
    date: datetime
    amount: Decimal
    partner: str | None = None


class DebtorBrief(BaseModel):
    customer_id: int
    full_name: str
    phone: str | None = None
    remaining: Decimal


class ChartPoint(BaseModel):
    label: str
    value: Decimal


class DashboardStats(BaseModel):
    """Aggregated dashboard figures."""

    today_stock_in_total: Decimal
    today_stock_out_total: Decimal
    today_sales_count: int
    today_profit: Decimal
    month_revenue: Decimal
    month_expense: Decimal
    debtors_count: int
    debtors_total: Decimal
    products_count: int
    total_stock_value: Decimal
    low_stock_count: int
    low_stock_products: list[LowStockProduct]
    top_products: list[TopProduct]
    debtors: list[DebtorBrief]
    recent_operations: list[RecentOperation]
    sales_chart: list[ChartPoint]
