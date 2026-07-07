"""Document sequence counter (Production Fix 4).

One row per ``(scope_type, scope_id)`` — e.g. ``("stock_in", company_id)`` or
``("sale", store_id)`` — holding the last-issued sequence number for that
scope. ``scope_id`` is nullable for the legacy single-tenant scope, using the
same partial-unique-index pattern as every other Option A table.
"""
from __future__ import annotations

from sqlalchemy import Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DocumentSequence(Base):
    """A per-scope monotonic counter, incremented atomically."""

    __tablename__ = "document_sequences"

    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", name="uq_document_sequences_scope"),
        Index(
            "uq_document_sequences_null_scope",
            "scope_type",
            unique=True,
            sqlite_where=text("scope_id IS NULL"),
            postgresql_where=text("scope_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentSequence {self.scope_type}:{self.scope_id}={self.last_value}>"
