"""User model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import UserRole
from app.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.role import Role


class User(Base, TimestampMixin, SoftDeleteMixin):
    """An application user who authenticates and performs operations.

    During the incremental multi-tenant migration this model carries two
    coexisting identity systems:

    - **Legacy RBAC** (``role_id`` / ``legacy_role`` / ``is_superuser``):
      the original configurable role/permission system. Kept fully
      functional for every existing user and router while they are migrated
      module by module.
    - **Multi-tenant identity** (``role`` / ``company_id`` / ``store_id``):
      the fixed Super Admin / CEO / Seller hierarchy from
      ``DATABASE_DESIGN.md`` §3.3. ``role`` already has its final,
      permanent name — nothing here will need renaming again once the
      legacy columns are eventually removed.
    """

    __tablename__ = "users"

    # Identity uniqueness is tenant-aware (DATABASE_DESIGN.md §6):
    #   - Company users are unique within their company: UNIQUE(company_id, username)
    #     and UNIQUE(company_id, email). Two different companies may each have a
    #     user named "admin" (NULL company_ids are distinct in these constraints,
    #     which also keeps them nullable-safe for email).
    #   - Super Admin / legacy users have company_id IS NULL and must remain
    #     globally unique among themselves, enforced by the partial indexes below.
    __table_args__ = (
        UniqueConstraint("company_id", "username", name="uq_users_company_username"),
        UniqueConstraint("company_id", "email", name="uq_users_company_email"),
        Index(
            "uq_users_null_company_username",
            "username",
            unique=True,
            sqlite_where=text("company_id IS NULL"),
            postgresql_where=text("company_id IS NULL"),
        ),
        Index(
            "uq_users_null_company_email",
            "email",
            unique=True,
            sqlite_where=text("company_id IS NULL AND email IS NOT NULL"),
            postgresql_where=text("company_id IS NULL AND email IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # --- Legacy RBAC (being phased out incrementally, module by module) ---
    # Nullable: users created through the new Companies/Employees flows (see
    # ``role`` below) have no legacy role assignment at all.
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Marks the built-in super administrator (protected account).
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Multi-tenant identity (DATABASE_DESIGN.md §3.3) ---
    # Nullable during the migration: only users created through the new
    # Companies/Employees flows have these set. A NULL ``role`` means "not
    # yet migrated to the new model" and such a user is never subject to the
    # new tenancy/role checks.
    role: Mapped[UserRole | None] = mapped_column(
        SAEnum(UserRole, name="user_role"), nullable=True, index=True
    )
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Relationships ---
    legacy_role: Mapped["Role"] = relationship(back_populates="users", lazy="selectin")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    @property
    def role_name(self) -> str:
        return self.legacy_role.name if self.legacy_role else ""

    def has_permission(self, code: str) -> bool:
        """Return True if the user's legacy role grants the given permission.

        Superusers implicitly hold every permission. This checks the legacy
        RBAC system only; the new fixed ``role`` is checked separately by
        the multi-tenant dependencies as each module is migrated.
        """
        if self.is_superuser:
            return True
        return bool(self.legacy_role and self.legacy_role.has_permission(code))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username}>"
