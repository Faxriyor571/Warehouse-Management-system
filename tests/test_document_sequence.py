"""Tests for the concurrency-safe document sequence service (Production Fix 4).

Verifies the atomic ``INSERT ... ON CONFLICT DO UPDATE ... RETURNING`` upsert:
sequential correctness, independent scopes (including the NULL/legacy scope),
reference-format preservation, and genuine multi-thread/multi-connection
concurrency (via a temp file-based SQLite database, so each thread gets its
own real connection rather than sharing the test suite's single pooled one).
"""
from __future__ import annotations

import tempfile
import threading
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.services import document_sequence_service as seq_service


def test_sequential_calls_increment(db_session: Session) -> None:
    values = [seq_service.next_sequence(db_session, "test_scope_a", 1) for _ in range(5)]
    db_session.commit()
    assert values == [1, 2, 3, 4, 5]


def test_independent_scope_ids(db_session: Session) -> None:
    a1 = seq_service.next_sequence(db_session, "test_scope_b", 10)
    b1 = seq_service.next_sequence(db_session, "test_scope_b", 20)
    a2 = seq_service.next_sequence(db_session, "test_scope_b", 10)
    db_session.commit()
    assert (a1, b1, a2) == (1, 1, 2)


def test_independent_scope_types(db_session: Session) -> None:
    a1 = seq_service.next_sequence(db_session, "test_scope_c1", 1)
    b1 = seq_service.next_sequence(db_session, "test_scope_c2", 1)
    a2 = seq_service.next_sequence(db_session, "test_scope_c1", 1)
    db_session.commit()
    assert (a1, b1, a2) == (1, 1, 2)


def test_null_scope_is_its_own_independent_counter(db_session: Session) -> None:
    legacy_1 = seq_service.next_sequence(db_session, "test_scope_d", None)
    tenant_1 = seq_service.next_sequence(db_session, "test_scope_d", 1)
    legacy_2 = seq_service.next_sequence(db_session, "test_scope_d", None)
    db_session.commit()
    assert (legacy_1, tenant_1, legacy_2) == (1, 1, 2)


def test_null_scope_never_duplicates_across_repeated_calls(db_session: Session) -> None:
    # Regression guard: a naive INSERT ON CONFLICT without a partial index for
    # NULL keys creates a new row every time (NULL != NULL in SQL), producing
    # duplicate "1" values instead of an incrementing counter.
    values = [seq_service.next_sequence(db_session, "test_scope_e", None) for _ in range(4)]
    db_session.commit()
    assert values == [1, 2, 3, 4]


def test_reference_format_preserved(db_session: Session) -> None:
    ref = seq_service.next_reference(db_session, scope_type="test_scope_f", scope_id=1, prefix="IN")
    db_session.commit()
    assert ref.startswith("IN-")
    parts = ref.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 8  # YYYYMMDD
    assert parts[2] == "000001"


def test_concurrent_threads_produce_unique_consecutive_values() -> None:
    """Genuine multi-connection concurrency: a temp file DB so each thread
    opens its own real connection (unlike the shared in-memory test engine)."""
    tmp_path = Path(tempfile.mkstemp(suffix=".db")[1])
    try:
        engine = create_engine(f"sqlite:///{tmp_path}")
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["document_sequences"]])
        SessionLocal = sessionmaker(bind=engine)

        results: list[int] = []
        lock = threading.Lock()
        threads_n, calls_per_thread = 8, 10

        def worker() -> None:
            db = SessionLocal()
            try:
                for _ in range(calls_per_thread):
                    value = seq_service.next_sequence(db, "concurrent_scope", 1)
                    db.commit()
                    with lock:
                        results.append(value)
            finally:
                db.close()

        threads = [threading.Thread(target=worker) for _ in range(threads_n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected_total = threads_n * calls_per_thread
        assert len(results) == expected_total
        assert len(set(results)) == expected_total, "duplicate sequence value produced under concurrency"
        assert sorted(results) == list(range(1, expected_total + 1))

        engine.dispose()
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except PermissionError:
            pass  # Windows may keep a brief handle open; the OS temp dir reclaims it later.
