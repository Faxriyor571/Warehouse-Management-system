"""Reporting schemas (API_SPECIFICATION.md §14 — JSON only, 4 report types)."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ChartPoint(BaseModel):
    label: str
    value: Decimal


# --- Sales ---------------------------------------------------------------
class PaymentStatusBucket(BaseModel):
    status: str  # paid | partial | unpaid
    count: int
    revenue: Decimal


class SalesReport(BaseModel):
    total_revenue: Decimal
    total_count: int
    by_payment_status: list[PaymentStatusBucket] = Field(default_factory=list)
    by_day: list[ChartPoint] = Field(default_factory=list)


# --- Inventory (current store_stock levels, by product) ------------------
class InventoryReportRow(BaseModel):
    product_id: int
    name: str
    sku: str
    quantity: Decimal


class InventoryReport(BaseModel):
    rows: list[InventoryReportRow] = Field(default_factory=list)
    count: int


# --- Debts (outstanding, grouped by customer and by status) --------------
class DebtByCustomer(BaseModel):
    customer_id: int
    full_name: str
    remaining: Decimal


class DebtByStatus(BaseModel):
    status: str  # active | overdue
    count: int
    remaining: Decimal


class DebtReport(BaseModel):
    by_customer: list[DebtByCustomer] = Field(default_factory=list)
    by_status: list[DebtByStatus] = Field(default_factory=list)
    total_remaining: Decimal


# --- Expenses (totals grouped by expense_type and by date) ---------------
class ExpenseByType(BaseModel):
    expense_type: str
    total: Decimal
    count: int


class ExpenseReport(BaseModel):
    by_type: list[ExpenseByType] = Field(default_factory=list)
    by_date: list[ChartPoint] = Field(default_factory=list)
    total: Decimal
