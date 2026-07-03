"""Audit log schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AuditAction
from app.schemas.stock_in import UserBrief


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    action: AuditAction
    entity_type: str | None = None
    entity_id: int | None = None
    description: str | None = None
    ip_address: str | None = None
    created_at: datetime
    user: UserBrief | None = None
