"""Role and Permission models (Role-Based Access Control).

A ``Role`` groups a set of ``Permission`` records via the ``role_permissions``
association table. Users are assigned exactly one role, and each role's
permissions are configurable independently.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


# Association table between roles and permissions (many-to-many).
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Permission(Base, TimestampMixin):
    """A single, fine-grained permission (e.g. ``product.create``)."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Machine name, e.g. "product.create", "debt.view".
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    # Human friendly name shown in the admin UI.
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    # Logical group for UI grouping, e.g. "product", "report".
    group: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Permission {self.code}>"


class Role(Base, TimestampMixin):
    """A role groups permissions and is assigned to users."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # System roles cannot be deleted from the admin panel.
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)

    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    users: Mapped[list["User"]] = relationship(back_populates="role")

    def has_permission(self, code: str) -> bool:
        return any(p.code == code for p in self.permissions)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role {self.name}>"
