"""Debt reminder endpoints (who to call today)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import DbSession
from app.permissions.dependencies import require_permission
from app.schemas.reminder import CallListEntry, ReminderSummary
from app.services import reminder_service

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get(
    "",
    response_model=ReminderSummary,
    dependencies=[Depends(require_permission("debt.view"))],
    summary="Qarz eslatmalari (bugun/ertaga/muddati o'tgan)",
)
def get_reminders(db: DbSession) -> ReminderSummary:
    return reminder_service.get_reminders(db)


@router.get(
    "/call-list",
    response_model=list[CallListEntry],
    dependencies=[Depends(require_permission("debt.view"))],
    summary="Bugungi qo'ng'iroqlar ro'yxati",
)
def get_call_list(db: DbSession) -> list[CallListEntry]:
    return reminder_service.get_call_list(db)
