"""Debt reminder schemas."""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class DebtReminder(BaseModel):
    """A single debt that needs attention (due soon / overdue)."""

    debt_id: int
    customer_id: int
    customer_name: str
    phone: str | None = None
    remaining_amount: Decimal
    due_date: date_type | None = None
    days_left: int | None = None  # negative => overdue
    status: str  # "due_today" | "due_tomorrow" | "overdue" | "upcoming"


class ReminderSummary(BaseModel):
    """Grouped reminders for the reminder dashboard / call list."""

    due_today: list[DebtReminder]
    due_tomorrow: list[DebtReminder]
    overdue: list[DebtReminder]
    upcoming: list[DebtReminder]
    total_count: int


class CallListEntry(BaseModel):
    """A simplified entry for the 'today's calls' list."""

    customer_id: int
    customer_name: str
    phone: str | None = None
    remaining_amount: Decimal
    due_date: date_type | None = None
    reason: str
