"""Audit log data-access operations."""
from __future__ import annotations

from app.crud.base import CRUDBase
from app.models.audit_log import AuditLog


class CRUDAuditLog(CRUDBase[AuditLog]):
    """CRUD operations for :class:`AuditLog`."""


audit_log = CRUDAuditLog(AuditLog)
