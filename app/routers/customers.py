"""Customer / farmer endpoints (API_SPECIFICATION.md §10).

Company-wide (no store scope): any Seller in the company can find/manage any
company customer, but a Seller's debt/sales history view is filtered to their
own store. The legacy single-tenant admin is admitted transitionally and
operates in the NULL-company scope. Super Admin has no access.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.legacy_compat import RequireCustomerActor, RequireCustomerManage
from app.crud.customer import customer as customer_crud
from app.models.customer import Customer
from app.models.enums import CustomerType, UserRole
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetail,
    CustomerOut,
    CustomerUpdate,
)
from app.services import customer_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/customers", tags=["Customers"])


def _resolve_scope(current_user: User) -> tuple[int | None, int | None]:
    """Resolve ``(company_id, store_filter)``.

    Customers themselves are company-wide (no store filter applies to the
    record itself); ``store_filter`` is only used to scope a Seller's
    debt/sales history view in the detail response.
    """
    if current_user.role == UserRole.SELLER:
        return current_user.company_id, current_user.store_id
    if current_user.role == UserRole.CEO:
        return current_user.company_id, None
    return None, None  # legacy single-tenant admin


def _get_customer_or_404(db: DbSession, current_user: User, customer_id: int) -> Customer:
    company_id, _ = _resolve_scope(current_user)
    obj = customer_crud.get_for_company(db, customer_id, company_id)
    if obj is None:
        raise NotFoundError(f"Mijoz (id={customer_id}) topilmadi")
    return obj


@router.get(
    "",
    response_model=PaginatedResponse[CustomerOut],
    summary="Mijozlar ro'yxati",
)
def list_customers(
    db: DbSession,
    current_user: RequireCustomerActor,
    search: str | None = Query(default=None),
    customer_type: CustomerType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[CustomerOut]:
    company_id, _ = _resolve_scope(current_user)
    params = PageParams(page=page, page_size=page_size)
    items, total = customer_crud.list_for_company(
        db, company_id, page_params=params, search=search, customer_type=customer_type
    )
    return PaginatedResponse[CustomerOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Mijoz qo'shish",
)
def create_customer(
    db: DbSession, ctx: ReqContext, current_user: RequireCustomerActor, data: CustomerCreate
) -> Customer:
    company_id, _ = _resolve_scope(current_user)
    return customer_service.create_customer(
        db,
        data,
        company_id=company_id,
        user_id=current_user.id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerDetail,
    summary="Mijoz ma'lumoti (qarz xulosasi va tarix bilan)",
)
def get_customer(
    db: DbSession, current_user: RequireCustomerActor, customer_id: int
) -> CustomerDetail:
    obj = _get_customer_or_404(db, current_user, customer_id)
    _, store_filter = _resolve_scope(current_user)
    summary = customer_service.get_debt_summary(db, customer_id, store_id=store_filter)
    purchases = customer_service.get_purchase_history(db, customer_id, store_id=store_filter)
    return CustomerDetail(
        **CustomerOut.model_validate(obj).model_dump(),
        debt_summary=summary,
        purchases=purchases,
    )


@router.put(
    "/{customer_id}",
    response_model=CustomerOut,
    summary="Mijozni yangilash",
)
def update_customer(
    db: DbSession,
    ctx: ReqContext,
    current_user: RequireCustomerActor,
    customer_id: int,
    data: CustomerUpdate,
) -> Customer:
    obj = _get_customer_or_404(db, current_user, customer_id)
    return customer_service.update_customer(
        db, obj, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )


@router.post(
    "/{customer_id}/deactivate",
    response_model=CustomerOut,
    summary="Mijozni faolsizlantirish",
)
def deactivate_customer(
    db: DbSession, ctx: ReqContext, current_user: RequireCustomerManage, customer_id: int
) -> Customer:
    obj = _get_customer_or_404(db, current_user, customer_id)
    return customer_service.deactivate_customer(
        db, obj, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )
