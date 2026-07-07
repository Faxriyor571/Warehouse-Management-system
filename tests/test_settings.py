"""Tests for the migrated Settings module (Phase 15, API_SPECIFICATION.md §15).

Company-scoped key/value store. CEO only (Seller none, Super Admin none;
legacy admin transitional). PUT accepts a single {key,value} or a batch
{settings:[...]}; response is a key/value map.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import security
from app.models.enums import UserRole
from app.models.user import User


def _make_super_admin(db: Session, username: str) -> None:
    db.add(
        User(
            username=username,
            full_name="Root",
            hashed_password=security.hash_password("Root12345!"),
            role_id=None,
            role=UserRole.SUPER_ADMIN,
            company_id=None,
            store_id=None,
            is_active=True,
        )
    )
    db.commit()


def _bearer(client: TestClient, username: str, password: str, company_slug: str | None = None) -> dict[str, str]:
    data = {"username": username, "password": password}
    if company_slug is not None:
        data["company_slug"] = company_slug
    resp = client.post("/api/v1/auth/login", data=data)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _onboard(client: TestClient, db: Session, slug: str) -> dict[str, str]:
    root = f"root-{slug}"
    _make_super_admin(db, root)
    sa = _bearer(client, root, "Root12345!")
    payload = {
        "name": f"Co {slug}",
        "slug": slug,
        "contact_email": None,
        "contact_phone": None,
        "ceo": {"username": f"ceo-{slug}", "full_name": "CEO", "password": "Ceo12345!", "email": None},
    }
    assert client.post("/api/v1/companies", headers=sa, json=payload).status_code == 201
    return _bearer(client, f"ceo-{slug}", "Ceo12345!", company_slug=slug)


def _store(client: TestClient, ceo: dict[str, str], name: str = "Store") -> int:
    return client.post("/api/v1/stores", headers=ceo, json={"name": name}).json()["id"]


def _seller(client: TestClient, ceo: dict[str, str], slug: str, username: str, store_id: int) -> dict[str, str]:
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Seller", "password": "Sell12345!", "store_id": store_id},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Sell12345!", company_slug=slug)


# ---------------------------------------------------------------------------
# CRUD behaviour
# ---------------------------------------------------------------------------
def test_empty_by_default(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "set-a")
    assert client.get("/api/v1/settings", headers=ceo).json() == {}


def test_single_upsert_and_read_back(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "set-b")
    resp = client.put("/api/v1/settings", headers=ceo, json={"key": "currency", "value": "UZS"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["currency"] == "UZS"
    assert client.get("/api/v1/settings", headers=ceo).json() == {"currency": "UZS"}


def test_upsert_overwrites_existing_key(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "set-c")
    client.put("/api/v1/settings", headers=ceo, json={"key": "currency", "value": "UZS"})
    client.put("/api/v1/settings", headers=ceo, json={"key": "currency", "value": "USD"})
    assert client.get("/api/v1/settings", headers=ceo).json() == {"currency": "USD"}


def test_batch_update(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "set-d")
    resp = client.put(
        "/api/v1/settings",
        headers=ceo,
        json={"settings": [{"key": "currency", "value": "UZS"}, {"key": "reminder_days", "value": "3"}]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"currency": "UZS", "reminder_days": "3"}


def test_null_value_allowed(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "set-e")
    resp = client.put("/api/v1/settings", headers=ceo, json={"key": "logo_url", "value": None})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"logo_url": None}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def test_rejects_both_forms_at_once(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "set-f")
    resp = client.put(
        "/api/v1/settings",
        headers=ceo,
        json={"key": "currency", "value": "UZS", "settings": [{"key": "x", "value": "y"}]},
    )
    assert resp.status_code == 422, resp.text


def test_rejects_empty_payload(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "set-g")
    assert client.put("/api/v1/settings", headers=ceo, json={}).status_code == 422


# ---------------------------------------------------------------------------
# Authorization / isolation
# ---------------------------------------------------------------------------
def test_seller_no_access(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "set-h")
    store_id = _store(client, ceo)
    seller = _seller(client, ceo, "set-h", "seller-set-h", store_id)
    assert client.get("/api/v1/settings", headers=seller).status_code == 403
    assert client.put("/api/v1/settings", headers=seller, json={"key": "x", "value": "y"}).status_code == 403


def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-set-i")
    sa = _bearer(client, "root-set-i", "Root12345!")
    assert client.get("/api/v1/settings", headers=sa).status_code == 403
    assert client.put("/api/v1/settings", headers=sa, json={"key": "x", "value": "y"}).status_code == 403


def test_company_isolation(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "set-j1")
    ceo_b = _onboard(client, db_session, "set-j2")
    client.put("/api/v1/settings", headers=ceo_a, json={"key": "currency", "value": "UZS"})

    assert client.get("/api/v1/settings", headers=ceo_b).json() == {}
    # Same key in company B is independent.
    client.put("/api/v1/settings", headers=ceo_b, json={"key": "currency", "value": "USD"})
    assert client.get("/api/v1/settings", headers=ceo_a).json() == {"currency": "UZS"}
    assert client.get("/api/v1/settings", headers=ceo_b).json() == {"currency": "USD"}
