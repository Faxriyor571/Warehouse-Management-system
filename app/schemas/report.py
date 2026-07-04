"""Reporting schemas."""
from __future__ import annotations

# The date type is imported under an alias: some rows have a field literally
# named ``date`` (e.g. SalesReportRow.date), and under
# ``from __future__ import annotations`` Pydantic v2 resolves annotations with
# the class namespace as locals, so a field named ``date`` could shadow the
# ``date`` type. Using ``date_type`` avoids that shadowing entirely.
from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    """A start/end date range used for report filtering."""

    date_from: date_type | None = None
    date_to: date_type | None = None


class SalesReportRow(BaseModel):
    reference: str
    date: date_type
    customer: str | None = None
    total_amount: Decimal
    paid_amount: Decimal
    payment_status: str


class SalesReport(BaseModel):
    rows: list[SalesReportRow] = Field(default_factory=list)
    total_amount: Decimal
    total_paid: Decimal
    count: int


class PurchaseReportRow(BaseModel):
    reference: str
    date: date_type
    supplier: str | None = None
    total_amount: Decimal


class PurchaseReport(BaseModel):
    rows: list[PurchaseReportRow] = Field(default_factory=list)
    total_amount: Decimal
    count: int


class DebtReportRow(BaseModel):
    customer: str
    phone: str | None = None
    amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    status: str
    due_date: date_type | None = None


class DebtReport(BaseModel):
    rows: list[DebtReportRow] = Field(default_factory=list)
    total_remaining: Decimal
    count: int


class InventoryReportRow(BaseModel):
    sku: str
    name: str
    quantity: Decimal
    purchase_price: Decimal
    sale_price: Decimal
    stock_value: Decimal


class InventoryReport(BaseModel):
    rows: list[InventoryReportRow] = Field(default_factory=list)
    total_stock_value: Decimal
    count: int


class ProfitReport(BaseModel):
    revenue: Decimal
    cost_of_goods: Decimal
    gross_profit: Decimal
    count: int
