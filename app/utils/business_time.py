"""Business-local (Uzbekistan) calendar-day helpers.

Uzbekistan has used a fixed UTC+5 offset year-round since abolishing DST in
1992 (no daylight-saving transitions), so a constant offset is sufficient —
no IANA tzdata lookup (``zoneinfo``) is required on the Python side, which
matters because the ``python:3.13-slim`` base image the backend runs on does
not ship the system tzdata package.

Every timestamp in this codebase is stored/compared in UTC (``func.now()``
server defaults, ``datetime.now(timezone.utc)``). That is correct for
storage, but the dashboard's "today" / "this month" and the expense date
default must reflect the shopkeeper's own calendar day, not the server's UTC
clock — otherwise anything recorded between local midnight and 05:00 (the
UTC+5 offset window) is silently attributed to the wrong day.

Deliberately pure-Python (range-comparison against plain UTC datetimes)
rather than a SQL-side ``timezone()``/``AT TIME ZONE`` expression: the test
suite runs against SQLite (``create_all``, see CLAUDE.md), which has no
``timezone()`` function, so any fix must be portable across both engines.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

#: Uzbekistan Standard Time — UTC+5, no DST observed.
BUSINESS_TZ = timezone(timedelta(hours=5))


def business_today() -> date:
    """Today's calendar date in business-local (UTC+5) time."""
    return datetime.now(BUSINESS_TZ).date()


def local_day_start_utc(local_day: date) -> datetime:
    """The UTC instant at 00:00 business-local time on ``local_day``.

    Use as a range boundary (``column >= local_day_start_utc(d)``) against a
    ``timestamptz`` column — portable across PostgreSQL and SQLite, unlike a
    SQL-side ``date()``/``timezone()`` truncation.
    """
    local_midnight = datetime.combine(local_day, time.min, tzinfo=BUSINESS_TZ)
    return local_midnight.astimezone(timezone.utc)


def to_local_date(instant: datetime) -> date:
    """The business-local calendar date a UTC (or naive-assumed-UTC) instant falls on."""
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(BUSINESS_TZ).date()
