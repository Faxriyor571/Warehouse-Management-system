"""Application settings endpoints (admin)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import DbSession
from app.crud.setting import setting as setting_crud
from app.models.setting import Setting
from app.permissions.dependencies import require_permission
from app.schemas.setting import SettingOut, SettingUpsert

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "",
    response_model=list[SettingOut],
    dependencies=[Depends(require_permission("setting.manage"))],
    summary="Sozlamalar ro'yxati",
)
def list_settings(db: DbSession) -> list[Setting]:
    return list(setting_crud.get_all(db))


@router.put(
    "",
    response_model=SettingOut,
    dependencies=[Depends(require_permission("setting.manage"))],
    summary="Sozlamani saqlash (yaratish yoki yangilash)",
)
def upsert_setting(db: DbSession, data: SettingUpsert) -> Setting:
    return setting_crud.upsert(db, data.key, data.value, data.description)
