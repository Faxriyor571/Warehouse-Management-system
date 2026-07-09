"""System Owner support sessions (SRS §3.1 / §2.2, amended).

The System Owner (``UserRole.SUPER_ADMIN``) exists above every company and
does not belong to one — but platform administration, customer support,
troubleshooting, and QA all require the ability to actually operate inside a
company: every store, employee, report, dashboard, setting, inventory, sale,
debt, and expense a CEO can see. Rather than duplicating that access across
every router's permission gate, a support session issues a short-lived,
access-token-only session scoped as the CEO of one company. Since a CEO
already has full access to everything in their company, this satisfies the
requirement exactly, through code that's already reviewed and correct.

``get_current_user`` (app/auth/dependencies.py) detects a token carrying a
``support_company_id`` claim and, after confirming the real user is actually
a System Owner, resolves it to an :class:`ActingUser` instead of the real
``User`` row. Every router and service downstream reads only the six
attributes below off ``current_user`` — confirmed by grepping the codebase —
so nothing else needs to change for the CEO-shaped pipeline to work
unmodified.

Deliberately **not** a SQLAlchemy model and never attached to the session:
mutating and committing the real System Owner's own ``User`` row to
impersonate a CEO would permanently corrupt their account. ``ActingUser`` is
a plain, disposable, request-scoped object instead.
"""
from __future__ import annotations

from datetime import datetime

from app.models.company import Company
from app.models.enums import UserRole
from app.models.user import User


class ActingUser:
    """A non-persisted CEO-equivalent identity for a System Owner's support session."""

    def __init__(self, real_user: User, *, company: Company) -> None:
        # Identity fields a support session inherits from the real System
        # Owner — kept so audit_service.log_action(user_id=current_user.id, ...)
        # attributes every action taken during the session to the real
        # person, not a fabricated identity.
        self.id = real_user.id
        self.username = real_user.username
        self.full_name = real_user.full_name
        self.email = real_user.email
        self.phone = real_user.phone
        self.role_id: int | None = None
        self.legacy_role = None
        self.created_at: datetime = real_user.created_at
        self.last_login_at: datetime | None = real_user.last_login_at
        self.is_active = real_user.is_active

        # Scoping fields — this is the CEO-equivalent view every router and
        # service actually authorizes and scopes against.
        self.is_superuser = False
        self.role: UserRole | None = UserRole.CEO
        self.company_id: int | None = company.id
        self.store_id: int | None = None

        # Support-session bookkeeping — surfaced by GET /auth/me so the
        # frontend can render the "acting as" banner with zero extra calls.
        self.is_support_session = True
        self.support_company_id: int | None = company.id
        self.support_company_name: str | None = company.name
