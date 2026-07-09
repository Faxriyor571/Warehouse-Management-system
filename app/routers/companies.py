"""Company endpoints (API_SPECIFICATION.md §2). Super Admin only."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession, require_super_admin
from app.crud.company import company as company_crud
from app.models.company import Company
from app.models.enums import CompanyStatus
from app.schemas.company import (
    CompanyCreate,
    CompanyCreateResponse,
    CompanyOut,
    CompanyUpdate,
    SupportSessionToken,
)
from app.schemas.common import PaginatedResponse
from app.services import company_service
from app.utils.pagination import PageParams, make_meta

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
    dependencies=[Depends(require_super_admin)],
)


@router.post(
    "",
    response_model=CompanyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi kompaniya onboarding (+ CEO)",
)
def create_company(db: DbSession, data: CompanyCreate) -> CompanyCreateResponse:
    company, ceo = company_service.create_company(db, data)
    return CompanyCreateResponse(company=company, ceo=ceo)  # type: ignore[arg-type]


@router.get("", response_model=PaginatedResponse[CompanyOut], summary="Kompaniyalar ro'yxati")
def list_companies(
    db: DbSession,
    search: str | None = Query(default=None, description="Nomi bo'yicha qidiruv"),
    status_filter: CompanyStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[CompanyOut]:
    filters = []
    if status_filter is not None:
        filters.append(Company.status == status_filter)

    params = PageParams(page=page, page_size=page_size)
    items, total = company_crud.list(
        db,
        page_params=params,
        search=search,
        search_fields=[Company.name],
        filters=filters,
        order_by=Company.id.desc(),
    )
    return PaginatedResponse[CompanyOut](items=items, meta=make_meta(total, params))


@router.get("/{company_id}", response_model=CompanyOut, summary="Kompaniya ma'lumoti")
def get_company(db: DbSession, company_id: int) -> Company:
    return company_crud.get_or_404(db, company_id)


@router.put("/{company_id}", response_model=CompanyOut, summary="Kompaniyani yangilash")
def update_company(db: DbSession, company_id: int, data: CompanyUpdate) -> Company:
    company = company_crud.get_or_404(db, company_id)
    return company_service.update_company(db, company, data)


@router.post("/{company_id}/activate", response_model=CompanyOut, summary="Kompaniyani faollashtirish")
def activate_company(db: DbSession, company_id: int) -> Company:
    company = company_crud.get_or_404(db, company_id)
    return company_service.activate_company(db, company)


@router.post("/{company_id}/suspend", response_model=CompanyOut, summary="Kompaniyani to'xtatish")
def suspend_company(db: DbSession, company_id: int) -> Company:
    company = company_crud.get_or_404(db, company_id)
    return company_service.suspend_company(db, company)


@router.post(
    "/{company_id}/support-session",
    response_model=SupportSessionToken,
    summary="Support session boshlash (System Owner ushbu kompaniyaga CEO sifatida kiradi)",
)
def start_support_session(db: DbSession, current_user: CurrentUser, company_id: int) -> SupportSessionToken:
    company, access_token = company_service.start_support_session(db, current_user, company_id)
    return SupportSessionToken(access_token=access_token, company=company)  # type: ignore[arg-type]
