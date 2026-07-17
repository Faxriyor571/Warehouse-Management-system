"""Report endpoints (API_SPECIFICATION.md §14). JSON only.

Each tab is gated by its own permission — ``Perm.REPORTS_SALES``/
``REPORTS_INVENTORY``/``REPORTS_DEBTS``/``REPORTS_EXPENSES`` — since the ERP
role redesign gives different roles different tabs (e.g. an Accountant sees
Debts/Expenses but not Sales/Inventory). A Cashier sees their own store only;
everyone else (CEO, Warehouse Employee, Accountant) sees the whole company or
one store via the ``store_id`` query param; the legacy admin bypasses via
``is_superuser`` (NULL scope). Super Admin has no access. Excel/PDF export and
the non-spec purchases/profit reports are intentionally not carried forward
(SRS Future Roadmap — API_SPECIFICATION.md §14/§16).
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import DbSession
from app.auth.permissions import require_perm
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.report import DebtReport, ExpenseReport, InventoryReport, SalesReport
from app.services import debt_service, report_service
from app.utils.scope import resolve_scope

router = APIRouter(prefix="/reports", tags=["Reports"])

RequireReportsSales = Annotated[User, Depends(require_perm(Perm.REPORTS_SALES))]
RequireReportsInventory = Annotated[User, Depends(require_perm(Perm.REPORTS_INVENTORY))]
RequireReportsDebts = Annotated[User, Depends(require_perm(Perm.REPORTS_DEBTS))]
RequireReportsExpenses = Annotated[User, Depends(require_perm(Perm.REPORTS_EXPENSES))]


@router.get("/sales", response_model=SalesReport, summary="Savdo hisoboti")
def sales_report(
    db: DbSession,
    current_user: RequireReportsSales,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
) -> SalesReport:
    company_id, store_filter = resolve_scope(current_user, store_id, db)
    return report_service.sales_report(
        db, company_id=company_id, store_id=store_filter, date_from=date_from, date_to=date_to
    )


@router.get("/inventory", response_model=InventoryReport, summary="Ombor hisoboti")
def inventory_report(
    db: DbSession,
    current_user: RequireReportsInventory,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
) -> InventoryReport:
    company_id, store_filter = resolve_scope(current_user, store_id, db)
    return report_service.inventory_report(db, company_id=company_id, store_id=store_filter)


@router.get("/debts", response_model=DebtReport, summary="Qarz hisoboti")
def debt_report(
    db: DbSession,
    current_user: RequireReportsDebts,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
) -> DebtReport:
    company_id, store_filter = resolve_scope(current_user, store_id, db)
    debt_service.refresh_overdue(db, company_id=company_id, store_id=store_filter)
    return report_service.debt_report(db, company_id=company_id, store_id=store_filter)


@router.get("/expenses", response_model=ExpenseReport, summary="Xarajatlar hisoboti")
def expense_report(
    db: DbSession,
    current_user: RequireReportsExpenses,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
) -> ExpenseReport:
    company_id, store_filter = resolve_scope(current_user, store_id, db)
    return report_service.expense_report(db, company_id=company_id, store_id=store_filter)
