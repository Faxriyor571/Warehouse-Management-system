"""Category endpoints (API_SPECIFICATION.md §5).

Company-scoped catalogue: writes are CEO-only, reads are CEO/Seller, Super
Admin has no access. Authorization goes through the transitional catalogue
dependencies in ``app/auth/legacy_compat.py`` (which also admit the legacy
single-tenant admin during migration). This router contains no legacy branch:
scoping is uniform via ``current_user.company_id`` (NULL for the legacy admin,
the company id for a CEO/Seller).
"""
from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.auth.dependencies import DbSession
from app.auth.legacy_compat import RequireCategoryManage, RequireCategoryRead
from app.crud.category import category as category_crud
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Message, PaginatedResponse
from app.services import category_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=PaginatedResponse[CategoryOut], summary="Kategoriyalar ro'yxati")
def list_categories(
    db: DbSession,
    current_user: RequireCategoryRead,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[CategoryOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = category_crud.list_for_company(
        db, current_user.company_id, page_params=params, search=search
    )
    return PaginatedResponse[CategoryOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Kategoriya qo'shish",
)
def create_category(
    db: DbSession, current_user: RequireCategoryManage, data: CategoryCreate
) -> Category:
    return category_service.create_category(db, current_user.company_id, data)


@router.get("/{category_id}", response_model=CategoryOut, summary="Kategoriya ma'lumoti")
def get_category(db: DbSession, current_user: RequireCategoryRead, category_id: int) -> Category:
    category = category_crud.get_for_company(db, category_id, current_user.company_id)
    if category is None:
        raise NotFoundError(f"Kategoriya (id={category_id}) topilmadi")
    return category


@router.put("/{category_id}", response_model=CategoryOut, summary="Kategoriyani yangilash")
def update_category(
    db: DbSession, current_user: RequireCategoryManage, category_id: int, data: CategoryUpdate
) -> Category:
    category = category_crud.get_for_company(db, category_id, current_user.company_id)
    if category is None:
        raise NotFoundError(f"Kategoriya (id={category_id}) topilmadi")
    return category_service.update_category(db, category, current_user.company_id, data)


@router.delete("/{category_id}", response_model=Message, summary="Kategoriyani o'chirish")
def delete_category(
    db: DbSession, current_user: RequireCategoryManage, category_id: int
) -> Message:
    category = category_crud.get_for_company(db, category_id, current_user.company_id)
    if category is None:
        raise NotFoundError(f"Kategoriya (id={category_id}) topilmadi")
    category_service.delete_category(db, category)
    return Message(detail="Kategoriya o'chirildi")
