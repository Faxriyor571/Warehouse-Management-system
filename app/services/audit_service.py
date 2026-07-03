"""Audit logging service.

Central place to record who did what. Never raises on logging failure so that
auditing cannot break a primary operation.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.enums import AuditAction

logger = logging.getLogger("wms.audit")


def log_action(
    db: Session,
    *,
    action: AuditAction,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    description: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = True,
) -> None:
    """Persist an audit log entry.

    Any exception is swallowed (and logged) because an audit failure must not
    abort the business operation that triggered it.
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(entry)
        if commit:
            db.commit()
    except Exception:  # pragma: no cover - defensive
        logger.exception("Audit log yozishda xatolik")
        db.rollback()
