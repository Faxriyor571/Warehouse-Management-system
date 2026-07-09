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


def test_create_company_reuses_ceo_username_across_companies(
    client: TestClient, db_session: Session
) -> None:
    """CEO usernames are unique per company, not globally (DATABASE_DESIGN.md §6).

    Two different companies may each onboard a CEO with the same username;
    company creation must succeed for both. (This previously asserted a
    global-uniqueness 409, which was the identity-scoping bug fixed here.)
    """
    headers = _super_admin_headers(client, db_session, username="root-c")
    client.post("/api/v1/companies", headers=headers, json=_company_payload("comp-c1"))

    dup = _company_payload("comp-c2")
    dup["ceo"]["username"] = "ceo-comp-c1"  # same username, different company
    resp = client.post("/api/v1/companies", headers=headers, json=dup)
    assert resp.status_code == 201


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


def test_support_session_grants_ceo_equivalent_access(
    client: TestClient, db_session: Session
) -> None:
    """A System Owner's support session must reach every module a CEO can.

    Exercises one representative module per SRS §3.1's amended list (store,
    dashboard, settings) rather than every single one — the mechanism is
    role/company_id substitution, not per-module logic, so one is
    representative of all of them.
    """
    headers = _super_admin_headers(client, db_session, username="root-h")
    created = client.post(
        "/api/v1/companies", headers=headers, json=_company_payload("comp-h")
    ).json()
    company_id = created["company"]["id"]

    session_resp = client.post(
        f"/api/v1/companies/{company_id}/support-session", headers=headers
    )
    assert session_resp.status_code == 200, session_resp.text
    body = session_resp.json()
    assert body["company"]["id"] == company_id
    assert "refresh_token" not in body

    support_headers = {"Authorization": f"Bearer {body['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=support_headers)
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["role"] == "ceo"
    assert me_body["company_id"] == company_id
    assert me_body["is_support_session"] is True
    assert me_body["support_company_name"] == created["company"]["name"]

    store_resp = client.post(
        "/api/v1/stores", headers=support_headers, json={"name": "Support Store"}
    )
    assert store_resp.status_code == 201, store_resp.text
    assert store_resp.json()["name"] == "Support Store"

    settings_resp = client.get("/api/v1/settings", headers=support_headers)
    assert settings_resp.status_code == 200

    dashboard_resp = client.get("/api/v1/dashboard", headers=support_headers)
    assert dashboard_resp.status_code == 200
    assert dashboard_resp.json()["scope"] == "company"


def test_support_session_requires_super_admin(client: TestClient, db_session: Session) -> None:
    headers = _super_admin_headers(client, db_session, username="root-i")
    created = client.post(
        "/api/v1/companies", headers=headers, json=_company_payload("comp-i")
    ).json()
    company_id = created["company"]["id"]

    ceo_login = client.post(
        "/api/v1/auth/login",
        data={"username": "ceo-comp-i", "password": "Ceo12345!", "company_slug": "comp-i"},
    ).json()
    ceo_headers = {"Authorization": f"Bearer {ceo_login['access_token']}"}

    resp = client.post(f"/api/v1/companies/{company_id}/support-session", headers=ceo_headers)
    assert resp.status_code == 403


def test_support_session_blocked_for_suspended_company(
    client: TestClient, db_session: Session
) -> None:
    headers = _super_admin_headers(client, db_session, username="root-j")
    created = client.post(
        "/api/v1/companies", headers=headers, json=_company_payload("comp-j")
    ).json()
    company_id = created["company"]["id"]
    client.post(f"/api/v1/companies/{company_id}/suspend", headers=headers)

    resp = client.post(f"/api/v1/companies/{company_id}/support-session", headers=headers)
    assert resp.status_code == 422
