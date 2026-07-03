"""Category CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession, ReqContext
from app.crud.category import category as category_crud
from app.models.category import Category
from app.models.enums import AuditAction
from app.permissions.dependencies import require_permission
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Message, PaginatedResponse
from app.services import audit_service
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=PaginatedResponse[CategoryOut],
    dependencies=[Depends(require_permission("category.view"))],
    summary="Kategoriyalar ro'yxati",
)
def list_categories(
    db: DbSession,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[CategoryOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = category_crud.list(
        db, page_params=params, search=search, search_fields=[Category.name]
    )
    return PaginatedResponse[CategoryOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("category.manage"))],
    summary="Kategoriya qo'shish",
)
def create_category(
    db: DbSession, ctx: ReqContext, current_user: CurrentUser, data: CategoryCreate
) -> Category:
    obj = category_crud.create(db, data.model_dump())
    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=current_user.id,
        entity_type="category",
        entity_id=obj.id,
        description=f"Kategoriya qo'shildi: {obj.name}",
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return obj


@router.get(
    "/{category_id}",
    response_model=CategoryOut,
    dependencies=[Depends(require_permission("category.view"))],
    summary="Kategoriya ma'lumoti",
)
def get_category(db: DbSession, category_id: int) -> Category:
    return category_crud.get_or_404(db, category_id)


@router.put(
    "/{category_id}",
    response_model=CategoryOut,
    dependencies=[Depends(require_permission("category.manage"))],
    summary="Kategoriyani yangilash",
)
def update_category(
    db: DbSession, current_user: CurrentUser, category_id: int, data: CategoryUpdate
) -> Category:
    obj = category_crud.get_or_404(db, category_id)
    updated = category_crud.update(db, obj, data.model_dump(exclude_unset=True))
    audit_service.log_action(
        db,
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        entity_type="category",
        entity_id=updated.id,
        description=f"Kategoriya yangilandi: {updated.name}",
    )
    return updated


@router.delete(
    "/{category_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("category.manage"))],
    summary="Kategoriyani o'chirish",
)
def delete_category(db: DbSession, current_user: CurrentUser, category_id: int) -> Message:
    obj = category_crud.get_or_404(db, category_id)
    category_crud.remove(db, obj)
    audit_service.log_action(
        db,
        action=AuditAction.DELETE,
        user_id=current_user.id,
        entity_type="category",
        entity_id=category_id,
        description=f"Kategoriya o'chirildi: {obj.name}",
    )
    return Message(detail="Kategoriya o'chirildi")
