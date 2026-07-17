"""Company settings endpoints (API_SPECIFICATION.md §15).

Company-scoped key/value configuration, gated by ``Perm.SETTINGS_MANAGE``
(CEO only — no employee job function grants it; the multi-tenant Super Admin
has no access either). The legacy single-tenant admin bypasses via
``is_superuser`` inside ``require_perm`` (NULL-company scope). Response is a
plain key/value map.

The generic key/value endpoints below (GET/PUT "") remain for API
compatibility, but the frontend Settings page no longer exposes them — a v1
simplification decision restricted Settings to the single field CEOs
actually need: their company's display name. GET/PUT "/company" is new here
for exactly that: no prior endpoint let a CEO rename their own company (only
a System Owner could, via PUT /companies/{id}, cross-tenant and gated to the
platform role) — a minimal, narrowly-scoped addition rather than widening
that existing endpoint's access.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import DbSession
from app.auth.permissions import require_perm
from app.crud.company import company as company_crud
from app.crud.setting import setting as setting_crud
from app.models.company import Company
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.company import CompanyNameUpdate, CompanyOut, CompanyUpdate
from app.schemas.setting import SettingsUpdate
from app.services import company_service
from app.utils.exceptions import ValidationError

router = APIRouter(prefix="/settings", tags=["Settings"])

RequireSettingsManage = Annotated[User, Depends(require_perm(Perm.SETTINGS_MANAGE))]


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


def _require_company(current_user: RequireSettingsManage, db: DbSession) -> Company:
    if current_user.company_id is None:
        raise ValidationError("Yagona tenant rejimida kompaniya profili mavjud emas")
    return company_crud.get_or_404(db, current_user.company_id)


@router.get("/company", response_model=CompanyOut, summary="Kompaniya nomi")
def get_company_profile(db: DbSession, current_user: RequireSettingsManage) -> Company:
    return _require_company(current_user, db)


@router.put("/company", response_model=CompanyOut, summary="Kompaniya nomini yangilash")
def update_company_profile(
    db: DbSession, current_user: RequireSettingsManage, data: CompanyNameUpdate
) -> Company:
    company = _require_company(current_user, db)
    return company_service.update_company(db, company, CompanyUpdate(name=data.name))
