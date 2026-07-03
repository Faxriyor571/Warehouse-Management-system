"""Reporting schemas."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    """A start/end date range used for report filtering."""

    date_from: date | None = None
    date_to: date | None = None


class SalesReportRow(BaseModel):
    reference: str
    date: date
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
    date: date
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
    due_date: date | None = None


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
