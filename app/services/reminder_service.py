"""Debt reminder logic: who to call today/tomorrow and who is overdue."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.debt import Debt
from app.schemas.reminder import CallListEntry, DebtReminder, ReminderSummary

# How many days ahead counts as "upcoming".
UPCOMING_WINDOW_DAYS = 7


def _load_open_debts(db: Session) -> list[tuple[Debt, Customer]]:
    stmt = (
        select(Debt, Customer)
        .join(Customer, Debt.customer_id == Customer.id)
        .where(Debt.remaining_amount > 0)
        .order_by(Debt.due_date.asc().nulls_last())
    )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def _to_reminder(debt: Debt, customer: Customer, days_left: int | None, status: str) -> DebtReminder:
    return DebtReminder(
        debt_id=debt.id,
        customer_id=customer.id,
        customer_name=customer.full_name,
        phone=customer.phone,
        remaining_amount=debt.remaining_amount,
        due_date=debt.due_date,
        days_left=days_left,
        status=status,
    )


def get_reminders(db: Session) -> ReminderSummary:
    """Group open debts into due-today / due-tomorrow / overdue / upcoming."""
    today = datetime.now(timezone.utc).date()
    due_today: list[DebtReminder] = []
    due_tomorrow: list[DebtReminder] = []
    overdue: list[DebtReminder] = []
    upcoming: list[DebtReminder] = []

    for debt, customer in _load_open_debts(db):
        if debt.due_date is None:
            continue
        days_left = (debt.due_date - today).days
        if days_left < 0:
            overdue.append(_to_reminder(debt, customer, days_left, "overdue"))
        elif days_left == 0:
            due_today.append(_to_reminder(debt, customer, days_left, "due_today"))
        elif days_left == 1:
            due_tomorrow.append(_to_reminder(debt, customer, days_left, "due_tomorrow"))
        elif days_left <= UPCOMING_WINDOW_DAYS:
            upcoming.append(_to_reminder(debt, customer, days_left, "upcoming"))

    total = len(due_today) + len(due_tomorrow) + len(overdue) + len(upcoming)
    return ReminderSummary(
        due_today=due_today,
        due_tomorrow=due_tomorrow,
        overdue=overdue,
        upcoming=upcoming,
        total_count=total,
    )


def get_call_list(db: Session) -> list[CallListEntry]:
    """Build today's call list: overdue debts plus those due today."""
    summary = get_reminders(db)
    entries: list[CallListEntry] = []
    for reminder in summary.overdue:
        entries.append(
            CallListEntry(
                customer_id=reminder.customer_id,
                customer_name=reminder.customer_name,
                phone=reminder.phone,
                remaining_amount=reminder.remaining_amount,
                due_date=reminder.due_date,
                reason="Muddati o'tgan",
            )
        )
    for reminder in summary.due_today:
        entries.append(
            CallListEntry(
                customer_id=reminder.customer_id,
                customer_name=reminder.customer_name,
                phone=reminder.phone,
                remaining_amount=reminder.remaining_amount,
                due_date=reminder.due_date,
                reason="Bugun muddati tugaydi",
            )
        )
    return entries
