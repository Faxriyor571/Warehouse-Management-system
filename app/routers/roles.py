"""Role and permission management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import DbSession
from app.crud.role import permission as permission_crud
from app.crud.role import role as role_crud
from app.models.role import Role
from app.permissions.dependencies import require_permission
from app.schemas.common import Message
from app.schemas.permission import PermissionOut
from app.schemas.role import RoleCreate, RoleOut, RoleUpdate
from app.utils.exceptions import ConflictError, ValidationError

router = APIRouter(tags=["Roles & Permissions"])


# ---------------------------------------------------------------------------
# Permissions (read-only catalogue)
# ---------------------------------------------------------------------------
@router.get(
    "/permissions",
    response_model=list[PermissionOut],
    dependencies=[Depends(require_permission("permission.view"))],
    summary="Barcha ruxsatlar",
)
def list_permissions(db: DbSession) -> list[PermissionOut]:
    return list(permission_crud.get_all(db))  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
@router.get(
    "/roles",
    response_model=list[RoleOut],
    dependencies=[Depends(require_permission("role.view"))],
    summary="Rollar ro'yxati",
)
def list_roles(db: DbSession) -> list[RoleOut]:
    return list(role_crud.get_all(db))  # type: ignore[return-value]


@router.post(
    "/roles",
    response_model=RoleOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("role.manage"))],
    summary="Yangi rol yaratish",
)
def create_role(db: DbSession, data: RoleCreate) -> Role:
    if role_crud.get_by_name(db, data.name) is not None:
        raise ConflictError(f"'{data.name}' nomli rol allaqachon mavjud")
    role = Role(name=data.name, description=data.description, is_system=False)
    role.permissions = permission_crud.get_by_codes(db, data.permission_codes)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get(
    "/roles/{role_id}",
    response_model=RoleOut,
    dependencies=[Depends(require_permission("role.view"))],
    summary="Rol ma'lumoti",
)
def get_role(db: DbSession, role_id: int) -> Role:
    return role_crud.get_or_404(db, role_id)


@router.put(
    "/roles/{role_id}",
    response_model=RoleOut,
    dependencies=[Depends(require_permission("role.manage"))],
    summary="Rolni yangilash",
)
def update_role(db: DbSession, role_id: int, data: RoleUpdate) -> Role:
    role = role_crud.get_or_404(db, role_id)
    if data.name is not None and data.name != role.name:
        if role_crud.get_by_name(db, data.name) is not None:
            raise ConflictError(f"'{data.name}' nomli rol allaqachon mavjud")
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.permission_codes is not None:
        role.permissions = permission_crud.get_by_codes(db, data.permission_codes)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.delete(
    "/roles/{role_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("role.manage"))],
    summary="Rolni o'chirish",
)
def delete_role(db: DbSession, role_id: int) -> Message:
    role = role_crud.get_or_404(db, role_id)
    if role.is_system:
        raise ValidationError("Tizim rolini o'chirib bo'lmaydi")
    if role.users:
        raise ValidationError("Rol foydalanuvchilarga biriktirilgan, o'chirib bo'lmaydi")
    role_crud.hard_delete(db, role)
    return Message(detail="Rol o'chirildi")
