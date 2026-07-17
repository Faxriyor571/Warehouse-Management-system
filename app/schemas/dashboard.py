"""Dashboard schemas (API_SPECIFICATION.md §13 — exact documented shape)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class TopProduct(BaseModel):
    product_id: int
    name: str
    quantity_sold: Decimal
    revenue: Decimal


class TopDebtor(BaseModel):
    customer_id: int
    full_name: str
    remaining: Decimal


class RecentOperation(BaseModel):
    type: Literal["sale", "stock_in"]
    reference: str
    date: datetime
    amount: Decimal


class ChartPoint(BaseModel):
    label: str
    value: Decimal


class DashboardStats(BaseModel):
    """Role-based dashboard summary — same shape for CEO and Seller, data
    scope differs (``scope``)."""

    scope: Literal["store", "company"]
    today_sales_total: Decimal
    today_sales_count: int
    month_revenue: Decimal
    month_expenses: Decimal
    debtors_count: int
    debtors_total: Decimal
    top_products: list[TopProduct]
    top_debtors: list[TopDebtor]
    recent_operations: list[RecentOperation]
    sales_chart: list[ChartPoint]
