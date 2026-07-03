"""End-to-end style tests: catalogue -> stock-in -> stock-out -> debt."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _create_category(client: TestClient, headers: dict[str, str], name: str) -> int:
    resp = client.post("/api/v1/categories", headers=headers, json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _first_unit_id(client: TestClient, headers: dict[str, str]) -> int:
    resp = client.get("/api/v1/units", headers=headers)
    assert resp.status_code == 200
    return resp.json()["items"][0]["id"]


def _create_product(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "name": "Test mahsulot",
        "sku": "SKU-TEST-1",
        "category_id": overrides["category_id"],
        "unit_id": overrides["unit_id"],
        "purchase_price": "10.00",
        "sale_price": "15.00",
        "min_quantity": "5",
        "quantity": "0",
    }
    payload.update({k: v for k, v in overrides.items() if k in payload})
    resp = client.post("/api/v1/products", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_full_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    category_id = _create_category(client, auth_headers, "Kategoriya A")
    unit_id = _first_unit_id(client, auth_headers)
    product = _create_product(
        client, auth_headers, category_id=category_id, unit_id=unit_id
    )
    product_id = product["id"]
    assert float(product["quantity"]) == 0.0

    # Stock-in: +100 units.
    resp = client.post(
        "/api/v1/stock-in",
        headers=auth_headers,
        json={
            "note": "Boshlang'ich kirim",
            "items": [{"product_id": product_id, "quantity": "100", "price": "10.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    assert client.get(f"/api/v1/products/{product_id}", headers=auth_headers).json()[
        "quantity"
    ] in ("100.000", "100.00", "100")

    # Create a customer.
    cust = client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={"full_name": "Ali Valiyev", "phone": "+998901234567"},
    )
    assert cust.status_code == 201, cust.text
    customer_id = cust.json()["id"]

    # Payment methods: find the CASH method id.
    methods = client.get("/api/v1/payment-methods", headers=auth_headers).json()
    cash_id = next(m["id"] for m in methods if m["type"] == "cash")

    # Stock-out: sell 10 @ 15 = 150, pay 100 cash -> remaining 50 becomes debt.
    resp = client.post(
        "/api/v1/stock-out",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "10", "price": "15.00"}],
            "payments": [{"payment_method_id": cash_id, "amount": "100.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    sale = resp.json()
    assert sale["payment_status"] == "partial"
    assert float(sale["total_amount"]) == 150.0
    assert float(sale["paid_amount"]) == 100.0

    # Inventory decreased to 90.
    remaining_qty = client.get(
        f"/api/v1/products/{product_id}", headers=auth_headers
    ).json()["quantity"]
    assert float(remaining_qty) == 90.0

    # A debt of 50 exists for the customer.
    debts = client.get(
        f"/api/v1/debts?customer_id={customer_id}", headers=auth_headers
    ).json()
    assert debts["meta"]["total"] == 1
    assert float(debts["items"][0]["remaining_amount"]) == 50.0


def test_insufficient_stock_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    category_id = _create_category(client, auth_headers, "Kategoriya B")
    unit_id = _first_unit_id(client, auth_headers)
    product = _create_product(
        client,
        auth_headers,
        category_id=category_id,
        unit_id=unit_id,
        sku="SKU-TEST-2",
    )
    resp = client.post(
        "/api/v1/stock-out",
        headers=auth_headers,
        json={
            "items": [{"product_id": product["id"], "quantity": "5", "price": "15.00"}],
            "payments": [],
        },
    )
    # No stock available -> validation error (422).
    assert resp.status_code == 422, resp.text
