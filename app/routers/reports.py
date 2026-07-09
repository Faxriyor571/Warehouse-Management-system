"""Report endpoints (API_SPECIFICATION.md §14). JSON only.

Company/store scoped: a Seller sees their own store only; a CEO sees the whole
company or one store via the ``store_id`` query param; the legacy admin is
transitional (NULL scope). Super Admin has no access. Excel/PDF export and the
non-spec purchases/profit reports are intentionally not carried forward
(SRS Future Roadmap — API_SPECIFICATION.md §14/§16).
"""
from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Query

from app.auth.dependencies import DbSession
from app.auth.legacy_compat import RequireReportsActor
from app.crud.store import store as store_crud
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.report import DebtReport, ExpenseReport, InventoryReport, SalesReport
from app.services import debt_service, report_service
from app.utils.exceptions import NotFoundError

router = APIRouter(prefix="/reports", tags=["Reports"])


def _resolve_scope(
    current_user: User, requested_store_id: int | None, db: DbSession
) -> tuple[int | None, int | None]:
    """Resolve ``(company_id, store_filter)``. ``store_id`` is a CEO-only
    filter; a Seller is always confined to their own store."""
    if current_user.role == UserRole.SELLER:
        return current_user.company_id, current_user.store_id
    if current_user.role == UserRole.CEO:
        if requested_store_id is not None:
            store = store_crud.get_for_company(db, requested_store_id, current_user.company_id)
            if store is None:
                raise NotFoundError(f"Do'kon (id={requested_store_id}) topilmadi")
        return current_user.company_id, requested_store_id
    return None, None  # legacy single-tenant admin


@router.get("/sales", response_model=SalesReport, summary="Savdo hisoboti")
def sales_report(
    db: DbSession,
    current_user: RequireReportsActor,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
) -> SalesReport:
    company_id, store_filter = _resolve_scope(current_user, store_id, db)
    return report_service.sales_report(
        db, company_id=company_id, store_id=store_filter, date_from=date_from, date_to=date_to
    )


@router.get("/inventory", response_model=InventoryReport, summary="Ombor hisoboti")
def inventory_report(
    db: DbSession,
    current_user: RequireReportsActor,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
) -> InventoryReport:
    company_id, store_filter = _resolve_scope(current_user, store_id, db)
    return report_service.inventory_report(db, company_id=company_id, store_id=store_filter)


@router.get("/debts", response_model=DebtReport, summary="Qarz hisoboti")
def debt_report(
    db: DbSession,
    current_user: RequireReportsActor,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
) -> DebtReport:
    company_id, store_filter = _resolve_scope(current_user, store_id, db)
    debt_service.refresh_overdue(db, company_id=company_id, store_id=store_filter)
    return report_service.debt_report(db, company_id=company_id, store_id=store_filter)


@router.get("/expenses", response_model=ExpenseReport, summary="Xarajatlar hisoboti")
def expense_report(
    db: DbSession,
    current_user: RequireReportsActor,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
) -> ExpenseReport:
    company_id, store_filter = _resolve_scope(current_user, store_id, db)
    return report_service.expense_report(db, company_id=company_id, store_id=store_filter)
