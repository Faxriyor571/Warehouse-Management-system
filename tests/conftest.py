"""Pytest fixtures.

Tests run against an in-memory SQLite database so they need no external
services. The ``get_db`` dependency is overridden to use the test session and
the schema + baseline data are created per test session.
"""
from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.db_init import seed_all
from app.main import app

# Single shared in-memory SQLite connection for the whole test run.
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> Generator[None, None, None]:
    # Import models so every table is registered on the metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=_engine)
    with TestingSessionLocal() as db:
        seed_all(db)
    yield
    Base.metadata.drop_all(bind=_engine)


def _override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client() -> TestClient:
    # Not used as a context manager, so the app lifespan (which would touch the
    # real PostgreSQL engine) does not run during tests.
    return TestClient(app)


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.first_admin_username,
            "password": settings.first_admin_password,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}
