"""Report endpoints with JSON output and Excel/PDF export."""
from __future__ import annotations

from datetime import date as date_type
from enum import Enum
from typing import Any, Sequence

from fastapi import APIRouter, Depends, Query, Response

from app.auth.dependencies import DbSession
from app.permissions.dependencies import require_permission
from app.schemas.report import (
    DebtReport,
    InventoryReport,
    ProfitReport,
    PurchaseReport,
    SalesReport,
)
from app.services import report_service
from app.utils.export import to_excel, to_pdf

router = APIRouter(prefix="/reports", tags=["Reports"])

_EXCEL_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_MEDIA = "application/pdf"


class ReportFormat(str, Enum):
    JSON = "json"
    EXCEL = "excel"
    PDF = "pdf"


def _export(
    fmt: ReportFormat,
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    filename: str,
) -> Response:
    """Return an Excel or PDF file response for the given table."""
    if fmt is ReportFormat.EXCEL:
        content = to_excel(title, headers, rows)
        media, ext = _EXCEL_MEDIA, "xlsx"
    else:
        content = to_pdf(title, headers, rows)
        media, ext = _PDF_MEDIA, "pdf"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{ext}"'},
    )


@router.get(
    "/sales",
    dependencies=[Depends(require_permission("report.view"))],
    summary="Savdo hisoboti",
    response_model=None,
)
def sales_report(
    db: DbSession,
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    fmt: ReportFormat = Query(default=ReportFormat.JSON, alias="format"),
) -> SalesReport | Response:
    report = report_service.sales_report(db, date_from, date_to)
    if fmt is ReportFormat.JSON:
        return report
    headers = ["Hujjat", "Sana", "Mijoz", "Jami", "To'langan", "Holat"]
    rows = [
        [r.reference, r.date, r.customer, r.total_amount, r.paid_amount, r.payment_status]
        for r in report.rows
    ]
    return _export(fmt, "Savdo hisoboti", headers, rows, "sales_report")


@router.get(
    "/purchases",
    dependencies=[Depends(require_permission("report.view"))],
    summary="Kirim (xarid) hisoboti",
    response_model=None,
)
def purchase_report(
    db: DbSession,
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    fmt: ReportFormat = Query(default=ReportFormat.JSON, alias="format"),
) -> PurchaseReport | Response:
    report = report_service.purchase_report(db, date_from, date_to)
    if fmt is ReportFormat.JSON:
        return report
    headers = ["Hujjat", "Sana", "Yetkazib beruvchi", "Jami"]
    rows = [[r.reference, r.date, r.supplier, r.total_amount] for r in report.rows]
    return _export(fmt, "Kirim hisoboti", headers, rows, "purchase_report")


@router.get(
    "/debts",
    dependencies=[Depends(require_permission("report.view"))],
    summary="Qarz hisoboti",
    response_model=None,
)
def debt_report(
    db: DbSession,
    only_open: bool = Query(default=False),
    fmt: ReportFormat = Query(default=ReportFormat.JSON, alias="format"),
) -> DebtReport | Response:
    report = report_service.debt_report(db, only_open=only_open)
    if fmt is ReportFormat.JSON:
        return report
    headers = ["Mijoz", "Telefon", "Summa", "To'langan", "Qoldiq", "Holat", "Muddat"]
    rows = [
        [r.customer, r.phone, r.amount, r.paid_amount, r.remaining_amount, r.status, r.due_date]
        for r in report.rows
    ]
    return _export(fmt, "Qarz hisoboti", headers, rows, "debt_report")


@router.get(
    "/inventory",
    dependencies=[Depends(require_permission("report.view"))],
    summary="Ombor (inventar) hisoboti",
    response_model=None,
)
def inventory_report(
    db: DbSession,
    fmt: ReportFormat = Query(default=ReportFormat.JSON, alias="format"),
) -> InventoryReport | Response:
    report = report_service.inventory_report(db)
    if fmt is ReportFormat.JSON:
        return report
    headers = ["SKU", "Nomi", "Miqdor", "Sotib olish", "Sotish", "Qiymati"]
    rows = [
        [r.sku, r.name, r.quantity, r.purchase_price, r.sale_price, r.stock_value]
        for r in report.rows
    ]
    return _export(fmt, "Ombor hisoboti", headers, rows, "inventory_report")


@router.get(
    "/profit",
    dependencies=[Depends(require_permission("report.view"))],
    summary="Foyda hisoboti",
    response_model=ProfitReport,
)
def profit_report(
    db: DbSession,
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
) -> ProfitReport:
    return report_service.profit_report(db, date_from, date_to)
