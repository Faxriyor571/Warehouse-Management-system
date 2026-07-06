"""Tests for the Companies module (Sprint 1, Phase 2). Super Admin only.

Super Admin accounts are not seeded anywhere yet (deliberately deferred —
production bootstrap strategy is a separate future task); this phase only
needs them to exist in the test environment, created directly via the
``db_session`` fixture, matching the pattern already used in
``test_auth_multitenant.py`` for CEO users.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import security
from app.config import settings
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole
from app.models.user import User


def _make_super_admin(db: Session, username: str = "root", password: str = "Root12345!") -> User:
    user = User(
        username=username,
        full_name="Platform Super Admin",
        hashed_password=security.hash_password(password),
        role_id=None,
        role=UserRole.SUPER_ADMIN,
        company_id=None,
        store_id=None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _super_admin_headers(client: TestClient, db_session: Session, username: str = "root") -> dict[str, str]:
    _make_super_admin(db_session, username=username)
    resp = client.post(
        "/api/v1/auth/login", data={"username": username, "password": "Root12345!"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _company_payload(slug: str) -> dict:
    return {
        "name": f"Acme {slug}",
        "slug": slug,
        "contact_email": "owner@example.com",
        "contact_phone": "+998901234567",
        "ceo": {
            "username": f"ceo-{slug}",
            "full_name": "Company CEO",
            "password": "Ceo12345!",
            "email": None,
        },
    }


def test_create_company_creates_ceo(client: TestClient, db_session: Session) -> None:
    headers = _super_admin_headers(client, db_session, username="root-a")
    resp = client.post(
        "/api/v1/companies", headers=headers, json=_company_payload("comp-a")
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["company"]["slug"] == "comp-a"
    assert body["company"]["status"] == "active"
    assert body["ceo"]["username"] == "ceo-comp-a"
    assert "password" not in body["ceo"]

    # The CEO can log in against the new company.
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-comp-a", "password": "Ceo12345!", "company_slug": "comp-a"},
    )
    assert login.status_code == 200


def test_create_company_duplicate_slug_rejected(client: TestClient, db_session: Session) -> None:
    headers = _super_admin_headers(client, db_session, username="root-b")
    client.post("/api/v1/companies", headers=headers, json=_company_payload("comp-b"))

    dup = _company_payload("comp-b")
    dup["ceo"]["username"] = "ceo-comp-b-2"
    resp = client.post("/api/v1/companies", headers=headers, json=dup)
    assert resp.status_code == 409


def test_create_company_duplicate_ceo_username_rejected(
    client: TestClient, db_session: Session
) -> None:
    headers = _super_admin_headers(client, db_session, username="root-c")
    client.post("/api/v1/companies", headers=headers, json=_company_payload("comp-c1"))

    dup = _company_payload("comp-c2")
    dup["ceo"]["username"] = "ceo-comp-c1"  # already used by comp-c1's CEO
    resp = client.post("/api/v1/companies", headers=headers, json=dup)
    assert resp.status_code == 409


def test_list_and_get_company(client: TestClient, db_session: Session) -> None:
    headers = _super_admin_headers(client, db_session, username="root-d")
    created = client.post(
        "/api/v1/companies", headers=headers, json=_company_payload("comp-d")
    ).json()

    listed = client.get("/api/v1/companies", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] >= 1

    detail = client.get(f"/api/v1/companies/{created['company']['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["slug"] == "comp-d"


def test_update_company_slug_immutable(client: TestClient, db_session: Session) -> None:
    headers = _super_admin_headers(client, db_session, username="root-e")
    created = client.post(
        "/api/v1/companies", headers=headers, json=_company_payload("comp-e")
    ).json()
    company_id = created["company"]["id"]

    resp = client.put(
        f"/api/v1/companies/{company_id}",
        headers=headers,
        json={"name": "Renamed Co", "contact_email": "new@example.com"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Renamed Co"
    assert body["slug"] == "comp-e"  # unchanged


def test_suspend_blocks_login_and_activate_restores(
    client: TestClient, db_session: Session
) -> None:
    headers = _super_admin_headers(client, db_session, username="root-f")
    created = client.post(
        "/api/v1/companies", headers=headers, json=_company_payload("comp-f")
    ).json()
    company_id = created["company"]["id"]

    suspend_resp = client.post(f"/api/v1/companies/{company_id}/suspend", headers=headers)
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["status"] == "suspended"

    blocked_login = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-comp-f", "password": "Ceo12345!", "company_slug": "comp-f"},
    )
    assert blocked_login.status_code == 401

    # Suspension must block login unconditionally — including when the
    # caller omits company_slug (a suspended company's CEO/Seller must not
    # be able to bypass the block simply by not naming their company).
    blocked_login_no_slug = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-comp-f", "password": "Ceo12345!"},
    )
    assert blocked_login_no_slug.status_code == 401

    activate_resp = client.post(f"/api/v1/companies/{company_id}/activate", headers=headers)
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "active"

    restored_login = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-comp-f", "password": "Ceo12345!", "company_slug": "comp-f"},
    )
    assert restored_login.status_code == 200


def test_ceo_cannot_access_companies(client: TestClient, db_session: Session) -> None:
    headers = _super_admin_headers(client, db_session, username="root-g")
    client.post("/api/v1/companies", headers=headers, json=_company_payload("comp-g"))

    ceo_login = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-comp-g", "password": "Ceo12345!", "company_slug": "comp-g"},
    ).json()
    ceo_headers = {"Authorization": f"Bearer {ceo_login['access_token']}"}

    resp = client.get("/api/v1/companies", headers=ceo_headers)
    assert resp.status_code == 403


def test_legacy_admin_cannot_access_companies(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """The legacy is_superuser bypass must not grant access to the new module."""
    resp = client.get("/api/v1/companies", headers=auth_headers)
    assert resp.status_code == 403
