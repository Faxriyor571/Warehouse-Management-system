"""Customer / farmer CRUD endpoints, with debt summary and purchase history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession
from app.crud.customer import customer as customer_crud
from app.models.customer import Customer
from app.models.enums import AuditAction
from app.permissions.dependencies import require_permission
from app.schemas.common import Message, PaginatedResponse
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetail,
    CustomerOut,
    CustomerUpdate,
)
from app.services import audit_service, customer_service
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get(
    "",
    response_model=PaginatedResponse[CustomerOut],
    dependencies=[Depends(require_permission("customer.view"))],
    summary="Mijozlar ro'yxati",
)
def list_customers(
    db: DbSession,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[CustomerOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = customer_crud.list(
        db,
        page_params=params,
        search=search,
        search_fields=[Customer.full_name, Customer.phone],
    )
    return PaginatedResponse[CustomerOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("customer.manage"))],
    summary="Mijoz qo'shish",
)
def create_customer(db: DbSession, current_user: CurrentUser, data: CustomerCreate) -> Customer:
    obj = customer_crud.create(db, data.model_dump())
    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=current_user.id,
        entity_type="customer",
        entity_id=obj.id,
        description=f"Mijoz qo'shildi: {obj.full_name}",
    )
    return obj


@router.get(
    "/{customer_id}",
    response_model=CustomerDetail,
    dependencies=[Depends(require_permission("customer.view"))],
    summary="Mijoz ma'lumoti (qarz xulosasi va tarix bilan)",
)
def get_customer(db: DbSession, customer_id: int) -> CustomerDetail:
    obj = customer_crud.get_or_404(db, customer_id)
    summary = customer_service.get_debt_summary(db, customer_id)
    purchases = customer_service.get_purchase_history(db, customer_id)
    return CustomerDetail(
        **CustomerOut.model_validate(obj).model_dump(),
        debt_summary=summary,
        purchases=purchases,
    )


@router.put(
    "/{customer_id}",
    response_model=CustomerOut,
    dependencies=[Depends(require_permission("customer.manage"))],
    summary="Mijozni yangilash",
)
def update_customer(
    db: DbSession, current_user: CurrentUser, customer_id: int, data: CustomerUpdate
) -> Customer:
    obj = customer_crud.get_or_404(db, customer_id)
    updated = customer_crud.update(db, obj, data.model_dump(exclude_unset=True))
    audit_service.log_action(
        db,
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        entity_type="customer",
        entity_id=updated.id,
        description=f"Mijoz yangilandi: {updated.full_name}",
    )
    return updated


@router.delete(
    "/{customer_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("customer.manage"))],
    summary="Mijozni o'chirish",
)
def delete_customer(db: DbSession, current_user: CurrentUser, customer_id: int) -> Message:
    obj = customer_crud.get_or_404(db, customer_id)
    customer_crud.remove(db, obj)
    audit_service.log_action(
        db,
        action=AuditAction.DELETE,
        user_id=current_user.id,
        entity_type="customer",
        entity_id=customer_id,
        description=f"Mijoz o'chirildi: {obj.full_name}",
    )
    return Message(detail="Mijoz o'chirildi")
