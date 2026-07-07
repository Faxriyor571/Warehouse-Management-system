"""Company settings endpoints (API_SPECIFICATION.md §15).

Company-scoped key/value configuration. CEO only (Seller and the multi-tenant
Super Admin have no access); the legacy single-tenant admin is admitted
transitionally (NULL-company scope). Response is a plain key/value map.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import DbSession
from app.auth.legacy_compat import RequireSettingsManage
from app.crud.setting import setting as setting_crud
from app.schemas.setting import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


def _as_map(db: DbSession, company_id: int | None) -> dict[str, str | None]:
    return {s.key: s.value for s in setting_crud.list_for_company(db, company_id)}


@router.get("", response_model=dict[str, str | None], summary="Kompaniya sozlamalari")
def get_settings(db: DbSession, current_user: RequireSettingsManage) -> dict[str, str | None]:
    return _as_map(db, current_user.company_id)


@router.put("", response_model=dict[str, str | None], summary="Sozlamalarni saqlash")
def update_settings(
    db: DbSession, current_user: RequireSettingsManage, data: SettingsUpdate
) -> dict[str, str | None]:
    for item in data.items():
        setting_crud.upsert(db, current_user.company_id, item.key, item.value, commit=False)
    db.commit()
    return _as_map(db, current_user.company_id)
