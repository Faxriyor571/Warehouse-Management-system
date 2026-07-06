"""Regression tests for company-scoped identity and company-first login.

Covers the two High-priority audit fixes:
- FIX 1: username/email uniqueness is per-company for company users, and
  global only among Super Admin / legacy users (company_id IS NULL) —
  DATABASE_DESIGN.md §6.
- FIX 2: login resolves company_slug -> Company -> username within company
  -> User -> password; no global username lookup for tenant users.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import security
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_super_admin(db: Session, username: str, email: str | None = None) -> User:
    sa = User(
        username=username,
        full_name="Root",
        email=email,
        hashed_password=security.hash_password("Root12345!"),
        role_id=None,
        role=UserRole.SUPER_ADMIN,
        company_id=None,
        store_id=None,
        is_active=True,
    )
    db.add(sa)
    db.commit()
    db.refresh(sa)
    return sa


def _sa_headers(client: TestClient, db: Session, username: str) -> dict[str, str]:
    _make_super_admin(db, username)
    resp = client.post("/api/v1/auth/login", data={"username": username, "password": "Root12345!"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _onboard(
    client: TestClient,
    sa_headers: dict[str, str],
    slug: str,
    ceo_username: str,
    ceo_email: str | None = None,
) -> dict:
    payload = {
        "name": f"Co {slug}",
        "slug": slug,
        "contact_email": None,
        "contact_phone": None,
        "ceo": {
            "username": ceo_username,
            "full_name": "CEO",
            "password": "Ceo12345!",
            "email": ceo_email,
        },
    }
    resp = client.post("/api/v1/companies", headers=sa_headers, json=payload)
    return resp


# ---------------------------------------------------------------------------
# FIX 1 — company-scoped uniqueness
# ---------------------------------------------------------------------------
def test_two_companies_share_ceo_username(client: TestClient, db_session: Session) -> None:
    """Two different companies may each have a user named the same (SRS #1/#2)."""
    sa = _sa_headers(client, db_session, "root-id-a")
    r1 = _onboard(client, sa, "id-a1", ceo_username="admin")
    r2 = _onboard(client, sa, "id-a2", ceo_username="admin")
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text  # would have been 409/500 under global uniqueness


def test_two_companies_share_ceo_email(client: TestClient, db_session: Session) -> None:
    sa = _sa_headers(client, db_session, "root-id-b")
    r1 = _onboard(client, sa, "id-b1", ceo_username="ceo1", ceo_email="shared@example.com")
    r2 = _onboard(client, sa, "id-b2", ceo_username="ceo2", ceo_email="shared@example.com")
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text


def test_duplicate_username_within_company_rejected(client: TestClient, db_session: Session) -> None:
    sa = _sa_headers(client, db_session, "root-id-c")
    created = _onboard(client, sa, "id-c", ceo_username="boss").json()
    company_id = created["company"]["id"]

    # A second user with the same username in the same company violates
    # UNIQUE(company_id, username).
    dup = User(
        username="boss",
        full_name="Impostor",
        hashed_password=security.hash_password("x12345"),
        role_id=None,
        role=UserRole.SELLER,
        company_id=company_id,
        store_id=None,
        is_active=True,
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_super_admins_globally_unique(client: TestClient, db_session: Session) -> None:
    """Super Admin / legacy users (company_id IS NULL) remain globally unique."""
    _make_super_admin(db_session, "root-id-d")
    dup = User(
        username="root-id-d",
        full_name="Root Dup",
        hashed_password=security.hash_password("x12345"),
        role_id=None,
        role=UserRole.SUPER_ADMIN,
        company_id=None,
        store_id=None,
        is_active=True,
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# FIX 2 — company-first login resolution
# ---------------------------------------------------------------------------
def test_same_username_resolves_per_company(client: TestClient, db_session: Session) -> None:
    """A shared username logs into the correct company via its own slug."""
    sa = _sa_headers(client, db_session, "root-id-e")
    a = _onboard(client, sa, "id-e1", ceo_username="admin").json()
    b = _onboard(client, sa, "id-e2", ceo_username="admin").json()

    login_a = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "Ceo12345!", "company_slug": "id-e1"},
    )
    login_b = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "Ceo12345!", "company_slug": "id-e2"},
    )
    assert login_a.status_code == 200
    assert login_b.status_code == 200

    me_a = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_a.json()['access_token']}"},
    ).json()
    me_b = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_b.json()['access_token']}"},
    ).json()
    assert me_a["company_id"] == a["company"]["id"]
    assert me_b["company_id"] == b["company"]["id"]
    assert me_a["id"] != me_b["id"]


def test_wrong_company_slug_rejected(client: TestClient, db_session: Session) -> None:
    sa = _sa_headers(client, db_session, "root-id-f")
    _onboard(client, sa, "id-f1", ceo_username="admin")
    _onboard(client, sa, "id-f2", ceo_username="other")

    # 'admin' exists in id-f1 but not id-f2 → must not resolve into id-f2.
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "Ceo12345!", "company_slug": "id-f2"},
    )
    assert resp.status_code == 401


def test_tenant_login_without_slug_rejected(client: TestClient, db_session: Session) -> None:
    """A CEO/Seller must supply company_slug; no global lookup resolves them."""
    sa = _sa_headers(client, db_session, "root-id-g")
    _onboard(client, sa, "id-g", ceo_username="admin")

    resp = client.post(
        "/api/v1/auth/login", data={"username": "admin", "password": "Ceo12345!"}
    )
    assert resp.status_code == 401


def test_super_admin_login_without_slug_still_works(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-id-h")
    resp = client.post(
        "/api/v1/auth/login", data={"username": "root-id-h", "password": "Root12345!"}
    )
    assert resp.status_code == 200


def test_super_admin_cannot_login_via_company_slug(client: TestClient, db_session: Session) -> None:
    """A Super Admin (company_id IS NULL) is not resolvable within a company."""
    sa = _sa_headers(client, db_session, "root-id-i")
    _onboard(client, sa, "id-i", ceo_username="ceo-id-i")

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "root-id-i", "password": "Root12345!", "company_slug": "id-i"},
    )
    assert resp.status_code == 401
