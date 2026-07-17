"""Migration-health tests (Production Fix 1).

These guard the Alembic migration chain without needing a live database:
- exactly one head (no divergent branches once more migrations land),
- a single base whose ``down_revision`` is None,
- every revision is importable/parseable and the model metadata is reachable.

Schema correctness itself (fresh DB via ``alembic upgrade head`` == models) was
verified against PostgreSQL by a zero-drift autogenerate check when the baseline
was created; that requires a live PG server and is not reproduced in the
SQLite-based test suite.
"""
from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models import Base

_ROOT = Path(__file__).resolve().parents[1]


def _script_dir() -> ScriptDirectory:
    cfg = Config(str(_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_ROOT / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_single_head() -> None:
    assert len(_script_dir().get_heads()) == 1, "Divergent Alembic heads — merge required"


def test_single_linear_base() -> None:
    script = _script_dir()
    bases = script.get_bases()
    assert len(bases) == 1
    base = script.get_revision(bases[0])
    assert base.down_revision is None


def test_all_revisions_parse() -> None:
    revisions = list(_script_dir().walk_revisions())
    assert revisions, "No Alembic migrations found"
    for rev in revisions:
        assert rev.module is not None


def test_metadata_has_expected_core_tables() -> None:
    # The baseline is generated from this metadata; sanity-check it is loaded.
    tables = set(Base.metadata.tables)
    for expected in ("companies", "stores", "products", "stock_outs", "debts", "expenses", "settings"):
        assert expected in tables
