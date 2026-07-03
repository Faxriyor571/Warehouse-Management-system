"""User management endpoints (admin) and self-service profile endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession, ReqContext
from app.crud.user import user as user_crud
from app.models.enums import AuditAction
from app.models.user import User
from app.permissions.dependencies import require_permission
from app.schemas.common import Message, PaginatedResponse
from app.schemas.user import (
    PasswordReset,
    PasswordUpdate,
    ProfileUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services import audit_service, user_service
from app.utils.pagination import PageParams, make_meta

router = APIRouter(tags=["Users"])


# ---------------------------------------------------------------------------
# Self-service profile (any authenticated user)
# ---------------------------------------------------------------------------
@router.put("/profile", response_model=UserOut, summary="O'z profilini yangilash")
def update_my_profile(db: DbSession, current_user: CurrentUser, data: ProfileUpdate) -> User:
    return user_service.update_profile(db, current_user, data)


@router.post("/profile/change-password", response_model=Message, summary="Parolni o'zgartirish")
def change_my_password(db: DbSession, current_user: CurrentUser, data: PasswordUpdate) -> Message:
    user_service.change_password(db, current_user, data)
    return Message(detail="Parol muvaffaqiyatli o'zgartirildi")


# ---------------------------------------------------------------------------
# Admin user management
# ---------------------------------------------------------------------------
@router.get(
    "/users",
    response_model=PaginatedResponse[UserOut],
    dependencies=[Depends(require_permission("user.view"))],
    summary="Foydalanuvchilar ro'yxati",
)
def list_users(
    db: DbSession,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[UserOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = user_crud.list(
        db,
        page_params=params,
        search=search,
        search_fields=[User.username, User.full_name, User.email],
    )
    return PaginatedResponse[UserOut](items=items, meta=make_meta(total, params))


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user.manage"))],
    summary="Yangi foydalanuvchi qo'shish",
)
def create_user(db: DbSession, ctx: ReqContext, current_user: CurrentUser, data: UserCreate) -> User:
    user = user_service.create_user(db, data)
    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user.id,
        description=f"Foydalanuvchi qo'shildi: {user.username}",
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return user


@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_permission("user.view"))],
    summary="Foydalanuvchi ma'lumoti",
)
def get_user(db: DbSession, user_id: int) -> User:
    return user_crud.get_or_404(db, user_id)


@router.put(
    "/users/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_permission("user.manage"))],
    summary="Foydalanuvchini yangilash",
)
def update_user(
    db: DbSession, ctx: ReqContext, current_user: CurrentUser, user_id: int, data: UserUpdate
) -> User:
    user = user_crud.get_or_404(db, user_id)
    updated = user_service.update_user(db, user, data)
    audit_service.log_action(
        db,
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user.id,
        description=f"Foydalanuvchi yangilandi: {updated.username}",
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return updated


@router.delete(
    "/users/{user_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("user.manage"))],
    summary="Foydalanuvchini o'chirish",
)
def delete_user(db: DbSession, ctx: ReqContext, current_user: CurrentUser, user_id: int) -> Message:
    user = user_crud.get_or_404(db, user_id)
    from app.utils.exceptions import ValidationError

    if user.is_superuser:
        raise ValidationError("Administratorni o'chirib bo'lmaydi")
    if user.id == current_user.id:
        raise ValidationError("O'zingizni o'chira olmaysiz")
    user_crud.remove(db, user)
    audit_service.log_action(
        db,
        action=AuditAction.DELETE,
        user_id=current_user.id,
        entity_type="user",
        entity_id=user_id,
        description=f"Foydalanuvchi o'chirildi: {user.username}",
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return Message(detail="Foydalanuvchi o'chirildi")


@router.post(
    "/users/{user_id}/reset-password",
    response_model=Message,
    dependencies=[Depends(require_permission("user.manage"))],
    summary="Parolni tiklash (admin)",
)
def reset_password(db: DbSession, user_id: int, data: PasswordReset) -> Message:
    user = user_crud.get_or_404(db, user_id)
    user_service.reset_password(db, user, data.new_password)
    return Message(detail="Parol tiklandi")


@router.post(
    "/users/{user_id}/activate",
    response_model=UserOut,
    dependencies=[Depends(require_permission("user.manage"))],
    summary="Foydalanuvchini faollashtirish",
)
def activate_user(db: DbSession, user_id: int) -> User:
    user = user_crud.get_or_404(db, user_id)
    return user_service.set_active(db, user, True)


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserOut,
    dependencies=[Depends(require_permission("user.manage"))],
    summary="Foydalanuvchini nofaol qilish",
)
def deactivate_user(db: DbSession, user_id: int) -> User:
    user = user_crud.get_or_404(db, user_id)
    return user_service.set_active(db, user, False)
