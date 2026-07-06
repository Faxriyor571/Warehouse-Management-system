"""Tests for the Stores module (Sprint 1, Phase 3).

Writes are CEO-only; reads are CEO/Seller with role-shaped responses. Super
Admin has no access. Sellers are inserted directly via the ``db_session``
fixture (the Employees API arrives in Phase 4), matching the direct-insert
pattern already used in earlier phases.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import security
from app.models.company import Company
from app.models.enums import CompanyStatus, UserRole
from app.models.store import Store
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


def _onboard_company(client: TestClient, db_session: Session, slug: str) -> dict[str, str]:
    """Create a company (+CEO) via the API and return CEO auth headers."""
    root = f"root-{slug}"
    _make_super_admin(db_session, root)
    sa_headers = _bearer(client, root, "Root12345!")
    payload = {
        "name": f"Co {slug}",
        "slug": slug,
        "contact_email": None,
        "contact_phone": None,
        "ceo": {
            "username": f"ceo-{slug}",
            "full_name": "CEO",
            "password": "Ceo12345!",
            "email": None,
        },
    }
    resp = client.post("/api/v1/companies", headers=sa_headers, json=payload)
    assert resp.status_code == 201, resp.text
    return _bearer(client, f"ceo-{slug}", "Ceo12345!", company_slug=slug)


def _make_seller(
    db: Session, company_slug: str, store_id: int, username: str, *, is_active: bool = True, deleted: bool = False
) -> User:
    from datetime import datetime, timezone

    company = db.query(Company).filter(Company.slug == company_slug).one()
    seller = User(
        username=username,
        full_name="Seller",
        hashed_password=security.hash_password("Sell12345!"),
        role_id=None,
        role=UserRole.SELLER,
        company_id=company.id,
        store_id=store_id,
        is_active=is_active,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller


def _create_store(client: TestClient, ceo_headers: dict[str, str], name: str = "Main Store") -> dict:
    resp = client.post(
        "/api/v1/stores",
        headers=ceo_headers,
        json={"name": name, "address": "Somewhere", "phone": "+998900000000"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def test_ceo_creates_store_company_from_token(client: TestClient, db_session: Session) -> None:
    ceo = _onboard_company(client, db_session, "st-a")
    body = _create_store(client, ceo)
    assert body["name"] == "Main Store"
    assert body["is_active"] is True
    # company_id is derived from the token; verify it points at this company.
    company = db_session.query(Company).filter(Company.slug == "st-a").one()
    assert body["company_id"] == company.id


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
def test_super_admin_cannot_access_stores(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-st-b")
    sa = _bearer(client, "root-st-b", "Root12345!")
    assert client.get("/api/v1/stores", headers=sa).status_code == 403
    assert client.post("/api/v1/stores", headers=sa, json={"name": "New Store"}).status_code == 403


def test_seller_cannot_write_stores(client: TestClient, db_session: Session) -> None:
    ceo = _onboard_company(client, db_session, "st-c")
    store = _create_store(client, ceo)
    seller = _make_seller(db_session, "st-c", store["id"], "seller-st-c")  # noqa: F841
    seller_headers = _bearer(client, "seller-st-c", "Sell12345!", company_slug="st-c")

    assert client.post("/api/v1/stores", headers=seller_headers, json={"name": "New Store"}).status_code == 403
    assert client.put(f"/api/v1/stores/{store['id']}", headers=seller_headers, json={"name": "Renamed"}).status_code == 403
    assert client.post(f"/api/v1/stores/{store['id']}/deactivate", headers=seller_headers).status_code == 403


def test_legacy_admin_cannot_access_stores(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The legacy is_superuser bypass must not grant access to the new module."""
    assert client.get("/api/v1/stores", headers=auth_headers).status_code == 403


# ---------------------------------------------------------------------------
# List — role-shaped response
# ---------------------------------------------------------------------------
def test_list_shapes_differ_by_role(client: TestClient, db_session: Session) -> None:
    ceo = _onboard_company(client, db_session, "st-d")
    store = _create_store(client, ceo)
    _make_seller(db_session, "st-d", store["id"], "seller-st-d")
    seller = _bearer(client, "seller-st-d", "Sell12345!", company_slug="st-d")

    ceo_list = client.get("/api/v1/stores", headers=ceo).json()
    assert len(ceo_list) == 1
    assert set(ceo_list[0]) >= {"id", "company_id", "name", "address", "phone", "is_active"}

    seller_list = client.get("/api/v1/stores", headers=seller).json()
    assert len(seller_list) == 1
    # Seller sees only id + name — no address/phone/is_active/company_id.
    assert set(seller_list[0]) == {"id", "name"}


# ---------------------------------------------------------------------------
# Tenant isolation & Seller detail scope
# ---------------------------------------------------------------------------
def test_ceo_cannot_access_other_company_store(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard_company(client, db_session, "st-e1")
    ceo_b = _onboard_company(client, db_session, "st-e2")
    store_b = _create_store(client, ceo_b)

    # CEO A must not see company B's store: 404 (not 403), to avoid leaking existence.
    assert client.get(f"/api/v1/stores/{store_b['id']}", headers=ceo_a).status_code == 404
    assert client.put(f"/api/v1/stores/{store_b['id']}", headers=ceo_a, json={"name": "Hack"}).status_code == 404


def test_seller_detail_scope(client: TestClient, db_session: Session) -> None:
    ceo = _onboard_company(client, db_session, "st-f")
    own = _create_store(client, ceo, name="Own")
    other = _create_store(client, ceo, name="Other")
    _make_seller(db_session, "st-f", own["id"], "seller-st-f")
    seller = _bearer(client, "seller-st-f", "Sell12345!", company_slug="st-f")

    assert client.get(f"/api/v1/stores/{own['id']}", headers=seller).status_code == 200
    # Same company, but not the Seller's assigned store → 403.
    assert client.get(f"/api/v1/stores/{other['id']}", headers=seller).status_code == 403


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
def test_ceo_updates_store(client: TestClient, db_session: Session) -> None:
    ceo = _onboard_company(client, db_session, "st-g")
    store = _create_store(client, ceo)
    resp = client.put(
        f"/api/v1/stores/{store['id']}", headers=ceo, json={"name": "Renamed", "phone": "+998911111111"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Renamed"
    assert body["phone"] == "+998911111111"


# ---------------------------------------------------------------------------
# Deactivate + Seller guard (the real business rule)
# ---------------------------------------------------------------------------
def test_deactivate_without_seller_succeeds(client: TestClient, db_session: Session) -> None:
    ceo = _onboard_company(client, db_session, "st-h")
    store = _create_store(client, ceo)
    resp = client.post(f"/api/v1/stores/{store['id']}/deactivate", headers=ceo)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_deactivate_blocked_by_active_seller(client: TestClient, db_session: Session) -> None:
    ceo = _onboard_company(client, db_session, "st-i")
    store = _create_store(client, ceo)
    _make_seller(db_session, "st-i", store["id"], "seller-st-i", is_active=True)

    resp = client.post(f"/api/v1/stores/{store['id']}/deactivate", headers=ceo)
    assert resp.status_code == 409


def test_deactivate_allowed_when_seller_inactive_or_deleted(client: TestClient, db_session: Session) -> None:
    """An inactive or soft-deleted former seller must NOT block deactivation.

    This is the difference between the real business rule and a bare
    User.store_id == store.id foreign-key check.
    """
    ceo = _onboard_company(client, db_session, "st-j")
    store = _create_store(client, ceo)
    _make_seller(db_session, "st-j", store["id"], "seller-st-j-inactive", is_active=False)
    _make_seller(db_session, "st-j", store["id"], "seller-st-j-deleted", deleted=True)

    resp = client.post(f"/api/v1/stores/{store['id']}/deactivate", headers=ceo)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
