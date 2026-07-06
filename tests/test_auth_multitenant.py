"""Tests for the additive multi-tenant authentication changes (Phase 1).

These exercise the new company_slug login path, JWT claims for users
migrated to the new identity model, and refresh-token rotation/revocation.
Legacy, single-tenant login behaviour is covered by ``test_auth.py`` and is
asserted here only once (``test_legacy_login_unaffected``) as a regression
sanity check, not duplicated further.
"""
from __future__ import annotations

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import security
from app.config import settings
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole
from app.models.role import Role
from app.models.user import User


def _make_company(
    db: Session, slug: str, status: CompanyStatus = CompanyStatus.ACTIVE
) -> Company:
    company = Company(name=f"Company {slug}", slug=slug, status=status)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _make_ceo(db: Session, company: Company, username: str, password: str = "Ceo12345!") -> User:
    # role_id remains NOT NULL (legacy RBAC untouched by this migration); any
    # seeded role works since this user is never checked against it.
    any_role = db.execute(select(Role)).scalars().first()
    assert any_role is not None, "expected db_init to have seeded at least one legacy role"

    user = User(
        username=username,
        full_name="Test CEO",
        hashed_password=security.hash_password(password),
        role_id=any_role.id,
        role=UserRole.CEO,
        company_id=company.id,
        store_id=None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_legacy_login_unaffected(client: TestClient) -> None:
    """The pre-existing single-tenant login path must be unchanged."""
    resp = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.first_admin_username,
            "password": settings.first_admin_password,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body


def test_tenant_login_with_matching_slug(client: TestClient, db_session: Session) -> None:
    company = _make_company(db_session, slug="tenant-a")
    _make_ceo(db_session, company, username="ceo-a")

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-a", "password": "Ceo12345!", "company_slug": "tenant-a"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["role"] == "ceo"
    assert payload["company_id"] == company.id
    assert payload["store_id"] is None


def test_tenant_login_wrong_slug_rejected(client: TestClient, db_session: Session) -> None:
    company_b = _make_company(db_session, slug="tenant-b")
    _make_ceo(db_session, company_b, username="ceo-b")
    _make_company(db_session, slug="tenant-c")

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-b", "password": "Ceo12345!", "company_slug": "tenant-c"},
    )
    assert resp.status_code == 401


def test_tenant_login_suspended_company_rejected(client: TestClient, db_session: Session) -> None:
    company = _make_company(db_session, slug="tenant-d", status=CompanyStatus.SUSPENDED)
    _make_ceo(db_session, company, username="ceo-d")

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-d", "password": "Ceo12345!", "company_slug": "tenant-d"},
    )
    assert resp.status_code == 401


def test_me_reflects_new_identity_fields(client: TestClient, db_session: Session) -> None:
    company = _make_company(db_session, slug="tenant-e")
    _make_ceo(db_session, company, username="ceo-e")

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-e", "password": "Ceo12345!", "company_slug": "tenant-e"},
    ).json()
    resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "ceo"
    assert body["company_id"] == company.id
    assert body["store_id"] is None
    # Legacy field renamed but still present/functional for existing routers.
    assert "legacy_role" in body


def test_refresh_token_rotation_revokes_previous(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.first_admin_username,
            "password": settings.first_admin_password,
        },
    ).json()

    first_refresh = login["refresh_token"]
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert refreshed.status_code == 200

    # Reusing the rotated-away token must now fail.
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert reused.status_code == 401


def test_logout_revokes_given_refresh_token(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    login = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.first_admin_username,
            "password": settings.first_admin_password,
        },
    ).json()

    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers=auth_headers,
        json={"refresh_token": login["refresh_token"]},
    )
    assert logout_resp.status_code == 200

    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert reuse.status_code == 401


def test_logout_without_body_still_works(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Existing no-body logout callers must be unaffected."""
    resp = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert resp.status_code == 200
