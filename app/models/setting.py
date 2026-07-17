"""Company setting model (Sozlamalar).

A per-company key/value store (DATABASE_DESIGN.md §3.23). ``company_id`` is
nullable for the legacy single-tenant scope (Option A); ``key`` is unique
within its company, enforced by the constraint below plus a NULL-scoped
partial index for legacy rows.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin


class Setting(Base, TimestampMixin):
    """A single key/value configuration entry, scoped to a company."""

    __tablename__ = "settings"

    __table_args__ = (
        UniqueConstraint("company_id", "key", name="uq_settings_company_key"),
        Index(
            "uq_settings_null_company_key",
            "key",
            unique=True,
            sqlite_where=text("company_id IS NULL"),
            postgresql_where=text("company_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Setting {self.key}={self.value!r}>"
