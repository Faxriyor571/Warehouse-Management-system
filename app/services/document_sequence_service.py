"""Concurrency-safe document reference numbering (Production Fix 4).

Replaces the previous ``SELECT count(*) + 1`` scheme — which races under
concurrent writers and can produce duplicate references — with a single
atomic ``INSERT ... ON CONFLICT DO UPDATE ... RETURNING`` upsert against a
dedicated per-scope counter (:class:`app.models.document_sequence.DocumentSequence`).

The upsert is a single statement, so PostgreSQL serializes concurrent callers
for the same ``(scope_type, scope_id)`` at the row level with no separate
lock step, no lost updates, and no duplicate values — including the very
first call for a scope (the ``INSERT`` half of the upsert creates the row).
SQLite (used by the test suite) supports the same ``ON CONFLICT`` syntax and
is single-writer regardless, so the identical code path is dialect-portable.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document_sequence import DocumentSequence
from app.utils.reference import generate_reference

_SUPPORTED_DIALECTS = {"postgresql", "sqlite"}


def _insert(db: Session):
    dialect = db.bind.dialect.name if db.bind is not None else "postgresql"
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        # Default to the PostgreSQL construct — the production dialect.
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    return dialect_insert


def next_sequence(db: Session, scope_type: str, scope_id: int | None) -> int:
    """Atomically allocate and return the next sequence value for a scope."""
    table = DocumentSequence.__table__
    insert = _insert(db)
    stmt = insert(table).values(scope_type=scope_type, scope_id=scope_id, last_value=1)
    if scope_id is None:
        stmt = stmt.on_conflict_do_update(
            index_elements=["scope_type"],
            index_where=table.c.scope_id.is_(None),
            set_={"last_value": table.c.last_value + 1},
        )
    else:
        stmt = stmt.on_conflict_do_update(
            index_elements=["scope_type", "scope_id"],
            set_={"last_value": table.c.last_value + 1},
        )
    stmt = stmt.returning(table.c.last_value)
    return db.execute(stmt).scalar_one()


def next_reference(db: Session, *, scope_type: str, scope_id: int | None, prefix: str) -> str:
    """Allocate the next sequence for a scope and format it as a reference
    (e.g. ``IN-20260707-000123``), preserving the existing format exactly.
    """
    sequence = next_sequence(db, scope_type, scope_id)
    return generate_reference(prefix, sequence)
