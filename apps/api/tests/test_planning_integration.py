"""Integration test uses only an explicitly named isolated test database."""

import os
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for database integration tests")
    assert url.rsplit("/", 1)[-1] == "pallet_building_test"
    assert os.getenv("APP_ENV") == "test"
    os.environ["DATABASE_URL"] = url
    from app.main import app
    return TestClient(app)


def test_session_scope_preflight_and_plan(client: TestClient) -> None:
    from app.db import SessionLocal
    from app.models import Membership, Organization, User
    from app.security import hash_password
    from app.tasks import process_run

    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        organization = Organization(name="Test org " + suffix)
        other = Organization(name="Other org " + suffix)
        admin = User(email=f"admin-{suffix}@palletbuilding.dev", display_name="Admin", password_hash=hash_password("long-test-password"))
        sales = User(email=f"sales-{suffix}@palletbuilding.dev", display_name="Sales", password_hash=hash_password("long-test-password"))
        warehouse = User(email=f"warehouse-{suffix}@palletbuilding.dev", display_name="Warehouse", password_hash=hash_password("long-test-password"))
        outsider = User(email=f"outsider-{suffix}@palletbuilding.dev", display_name="Outsider", password_hash=hash_password("long-test-password"))
        db.add_all([organization, other, admin, sales, warehouse, outsider])
        db.flush()
        db.add_all([Membership(organization_id=organization.id, user_id=admin.id, role="admin"), Membership(organization_id=organization.id, user_id=sales.id, role="sales"), Membership(organization_id=organization.id, user_id=warehouse.id, role="warehouse"), Membership(organization_id=other.id, user_id=outsider.id, role="sales")])
        db.commit()
    assert client.get("/api/v1/me").status_code == 401
    login = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "long-test-password"}, headers={"Origin": "http://localhost:3000"})
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": csrf}
    assert client.post("/api/v1/products", json={"sku": "X", "name": "X"}).status_code == 403
    product = client.post("/api/v1/products", json={"sku": "X-" + suffix, "name": "Carton"}, headers=headers)
    assert product.status_code == 201, product.text
    unit = client.post("/api/v1/packaging-units", json={"product_id": product.json()["id"], "code": "BOX", "units_per_package": 12, "length_mm": 400, "width_mm": 300, "height_mm": 200, "mass_g": 5000}, headers=headers)
    assert unit.status_code == 201, unit.text
    verification = client.post(f"/api/v1/packaging-units/{unit.json()['id']}/verify", json={"expected_revision": 1, "evidence_ref": "synthetic-test-fixture", "top_load_limit_g": 10000, "allow_upright_90": True}, headers=headers)
    assert verification.status_code == 200, verification.text
    pallet = client.post("/api/v1/pallet-types", json={"code": "TEST-" + suffix, "length_mm": 1200, "width_mm": 800, "deck_height_mm": 144, "max_total_height_mm": 544, "max_cargo_mass_g": 100000, "tare_mass_g": 25000, "available_count": 1, "support_model": "solid_deck", "evidence_ref": "synthetic-test-fixture"}, headers=headers)
    assert pallet.status_code == 201, pallet.text
    customer = client.post("/api/v1/customers", json={"external_ref": "C-" + suffix, "name": "Customer", "contact_name": "Dock manager", "contact_email": "dock@example.com", "ship_to_address_line1": "1 Test Street", "ship_to_city": "Prague", "ship_to_postal_code": "11000", "ship_to_country_code": "CZ"}, headers=headers)
    assert customer.status_code == 201, customer.text
    customer_id = customer.json()["id"]
    updated_customer = client.put(f"/api/v1/customers/{customer_id}", json={**{key: customer.json()[key] for key in ("external_ref", "name", "contact_name", "contact_email", "contact_phone", "ship_to_name", "ship_to_address_line1", "ship_to_address_line2", "ship_to_city", "ship_to_postal_code", "ship_to_country_code", "delivery_instructions")}, "expected_revision": 1, "contact_phone": "+420 123 456 789"}, headers=headers)
    assert updated_customer.status_code == 200, updated_customer.text
    assert updated_customer.json()["revision"] == 2
    assert updated_customer.json()["contact_phone"] == "+420 123 456 789"
    assert client.put(f"/api/v1/customers/{customer_id}", json={**updated_customer.json(), "expected_revision": 1}, headers=headers).status_code == 409
    assert client.put("/api/v1/customers/not-a-uuid", json={**updated_customer.json(), "expected_revision": 2}, headers=headers).status_code == 422
    assert client.post("/api/v1/customers", json={"external_ref": "C-" + suffix, "name": "Duplicate"}, headers=headers).status_code == 409
    assert client.get("/api/v1/customers").json()[0]["ship_to_country_code"] == "CZ"
    order = client.post("/api/v1/orders", json={"order_ref": "O-" + suffix, "customer_id": customer.json()["id"]}, headers=headers)
    line = client.post(f"/api/v1/orders/{order.json()['id']}/lines", json={"packaging_unit_id": unit.json()["id"], "line_no": 1, "quantity_units": 192}, headers=headers)
    assert line.status_code == 201, line.text
    shipment = client.post(f"/api/v1/orders/{order.json()['id']}/shipments", json={"shipment_ref": "S-" + suffix, "lines": [{"packaging_unit_id": unit.json()["id"], "line_no": 1, "quantity_units": 192}]}, headers=headers)
    assert shipment.status_code == 201, shipment.text
    shipment_id = shipment.json()["id"]
    blocked = client.post(f"/api/v1/orders/{order.json()['id']}/shipments", json={"shipment_ref": "OVER-" + suffix, "lines": [{"packaging_unit_id": unit.json()["id"], "line_no": 1, "quantity_units": 12}]}, headers=headers)
    assert blocked.status_code == 409
    report = client.post(f"/api/v1/shipments/{shipment_id}/preflight", json={"pallet_type_id": pallet.json()["id"]}, headers=headers)
    assert report.json()["ready"] is True
    assert report.json()["requested_cartons"] == 16
    run_payload = {"pallet_type_id": pallet.json()["id"], "expected_shipment_revision": 1}
    run_headers = {**headers, "Idempotency-Key": "test-" + suffix}
    cors = client.options(f"/api/v1/shipments/{shipment_id}/runs", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,x-csrf-token,idempotency-key"})
    assert cors.status_code == 200
    assert "idempotency-key" in cors.headers["access-control-allow-headers"].lower()
    run = client.post(f"/api/v1/shipments/{shipment_id}/runs", json=run_payload, headers=run_headers)
    assert run.status_code == 202, run.text
    assert client.get(f"/api/v1/shipments/{shipment_id}/runs").json()[0]["id"] == run.json()["id"]
    assert client.post(f"/api/v1/shipments/{shipment_id}/runs", json=run_payload, headers=run_headers).json()["id"] == run.json()["id"]
    conflicting = client.post(f"/api/v1/shipments/{shipment_id}/runs", json={**run_payload, "expected_shipment_revision": 2}, headers=run_headers)
    assert conflicting.status_code == 409
    assert conflicting.json()["detail"] == "IDEMPOTENCY_KEY_CONFLICT"
    if os.getenv("RUN_ASYNC_SMOKE") == "1":
        from app.dispatcher import dispatch_once
        assert dispatch_once() >= 1
        for _ in range(50):
            if client.get(f"/api/v1/runs/{run.json()['id']}").json()["status"] == "succeeded":
                break
            time.sleep(0.2)
    else:
        assert process_run(__import__("uuid").UUID(run.json()["id"])) == "succeeded"
    completed = client.get(f"/api/v1/runs/{run.json()['id']}").json()
    assert completed["status"] == "succeeded"
    assert process_run(__import__("uuid").UUID(run.json()["id"])) == "succeeded"
    plan = client.get(f"/api/v1/plans/{completed['plan_id']}").json()
    assert len(plan["layout"]["placed"]) == 16
    assert plan["layout"]["loaded_height_mm"] == 544
    assert plan["layout"]["loaded_mass_g"] == 105000
    assert plan["layout"]["model_checks"]["transport_dynamics"] == "not_evaluated"
    assert plan["layout"]["model_checks"]["instruction_prefix"] == "passed"
    second_product = client.post("/api/v1/products", json={"sku": "Y-" + suffix, "name": "Second carton"}, headers=headers).json()
    second_unit = client.post("/api/v1/packaging-units", json={"product_id": second_product["id"], "code": "BOX-B", "units_per_package": 1, "length_mm": 300, "width_mm": 400, "height_mm": 100, "mass_g": 2000}, headers=headers).json()
    assert client.post(f"/api/v1/packaging-units/{second_unit['id']}/verify", json={"expected_revision": 1, "evidence_ref": "synthetic-mixed-fixture", "top_load_limit_g": None, "allow_upright_90": False}, headers=headers).status_code == 200
    mixed_order = client.post("/api/v1/orders", json={"order_ref": "MIX-" + suffix, "customer_id": customer.json()["id"]}, headers=headers).json()
    for number, unit_id, quantity in ((1, unit.json()["id"], 24), (2, second_unit["id"], 2)):
        assert client.post(f"/api/v1/orders/{mixed_order['id']}/lines", json={"packaging_unit_id": unit_id, "line_no": number, "quantity_units": quantity}, headers=headers).status_code == 201
    mixed_shipment = client.post(f"/api/v1/orders/{mixed_order['id']}/shipments", json={"shipment_ref": "MIX-S-" + suffix, "lines": [{"packaging_unit_id": unit.json()["id"], "line_no": 1, "quantity_units": 24}, {"packaging_unit_id": second_unit["id"], "line_no": 2, "quantity_units": 2}]}, headers=headers)
    assert mixed_shipment.status_code == 201, mixed_shipment.text
    mixed_report = client.post(f"/api/v1/shipments/{mixed_shipment.json()['id']}/preflight", json={"pallet_type_id": pallet.json()["id"]}, headers=headers).json()
    assert mixed_report["ready"] is True
    assert mixed_report["requested_cartons"] == 4
    mixed_run = client.post(f"/api/v1/shipments/{mixed_shipment.json()['id']}/runs", json={"pallet_type_id": pallet.json()["id"], "expected_shipment_revision": 1}, headers={**headers, "Idempotency-Key": "mixed-" + suffix})
    assert mixed_run.status_code == 202, mixed_run.text
    assert process_run(__import__("uuid").UUID(mixed_run.json()["id"])) == "succeeded"
    mixed_plan_id = client.get(f"/api/v1/runs/{mixed_run.json()['id']}").json()["plan_id"]
    mixed_layout = client.get(f"/api/v1/plans/{mixed_plan_id}").json()["layout"]
    assert mixed_layout["requested_instances"] == 4
    assert mixed_layout["placed_instances"] + mixed_layout["unplaced_instances"] == 4
    assert {item["sku"] for item in mixed_layout["placed"]} == {product.json()["sku"], second_product["sku"]}
    best_payload = {"pallet_type_id": pallet.json()["id"], "expected_shipment_revision": 1, "strategy": "best_fit", "evaluation_budget": 10000}
    best_run = client.post(f"/api/v1/shipments/{mixed_shipment.json()['id']}/runs", json=best_payload, headers={**headers, "Idempotency-Key": "best-" + suffix})
    assert best_run.status_code == 202, best_run.text
    assert process_run(__import__("uuid").UUID(best_run.json()["id"])) == "succeeded"
    best_plan_id = client.get(f"/api/v1/runs/{best_run.json()['id']}").json()["plan_id"]
    best_layout = client.get(f"/api/v1/plans/{best_plan_id}").json()["layout"]
    assert best_layout["search"]["strategy"] == "best_fit"
    assert best_layout["search"]["candidates_completed"] > 1
    assert best_layout["unplaced_instances"] <= mixed_layout["unplaced_instances"]
    assert client.post(f"/api/v1/shipments/{mixed_shipment.json()['id']}/runs", json={**best_payload, "strategy": "quick"}, headers={**headers, "Idempotency-Key": "best-" + suffix}).status_code == 409
    assert client.get(f"/api/v1/plans/{completed['plan_id']}").json()["layout_hash"] == plan["layout_hash"]
    basket_order = client.post("/api/v1/orders", json={"order_ref": "CART-" + suffix, "customer_id": customer.json()["id"]}, headers=headers).json()
    basket_body = {"expected_revision": 1, "lines": [{"packaging_unit_id": unit.json()["id"], "quantity_cartons": 2}, {"packaging_unit_id": second_unit["id"], "quantity_cartons": 3}]}
    saved_cart = client.put(f"/api/v1/orders/{basket_order['id']}/cart", json=basket_body, headers=headers)
    assert saved_cart.status_code == 200, saved_cart.text
    assert [line["quantity_units"] for line in saved_cart.json()["lines"]] == [24, 3]
    assert client.get(f"/api/v1/orders/{basket_order['id']}").json()["revision"] == 2
    assert client.put(f"/api/v1/orders/{basket_order['id']}/cart", json=basket_body, headers=headers).status_code == 409
    basket_shipment = client.post(f"/api/v1/orders/{basket_order['id']}/shipments", json={"shipment_ref": "CART-S-" + suffix, "lines": [{"packaging_unit_id": line["packaging_unit_id"], "line_no": line["line_no"], "quantity_units": line["quantity_units"]} for line in saved_cart.json()["lines"]]}, headers=headers)
    assert basket_shipment.status_code == 201, basket_shipment.text
    assert client.put(f"/api/v1/orders/{basket_order['id']}/cart", json={**basket_body, "expected_revision": 2}, headers=headers).status_code == 409
    client.cookies.clear()
    sales_login = client.post("/api/v1/auth/login", json={"email": sales.email, "password": "long-test-password"}, headers={"Origin": "http://localhost:3000"})
    sales_headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": sales_login.json()["csrf_token"]}
    assert client.get(f"/api/v1/plans/{mixed_plan_id}").status_code == 200
    assert client.post(f"/api/v1/shipments/{shipment_id}/preflight", json={"pallet_type_id": pallet.json()["id"]}, headers=sales_headers).status_code == 403
    assert client.post(f"/api/v1/shipments/{shipment_id}/runs", json=run_payload, headers={**sales_headers, "Idempotency-Key": "sales-denied-" + suffix}).status_code == 403
    client.cookies.clear()
    warehouse_login = client.post("/api/v1/auth/login", json={"email": warehouse.email, "password": "long-test-password"}, headers={"Origin": "http://localhost:3000"})
    warehouse_headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": warehouse_login.json()["csrf_token"]}
    assert client.post(f"/api/v1/shipments/{shipment_id}/preflight", json={"pallet_type_id": pallet.json()["id"]}, headers=warehouse_headers).status_code == 200
    assert client.post("/api/v1/products", json={"sku": "DENIED-" + suffix, "name": "Denied"}, headers=warehouse_headers).status_code == 403
    assert client.put(f"/api/v1/customers/{customer_id}", json={**updated_customer.json(), "expected_revision": 2}, headers=warehouse_headers).status_code == 403
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json={"email": outsider.email, "password": "long-test-password"}, headers={"Origin": "http://localhost:3000"}).status_code == 200
    assert client.get(f"/api/v1/plans/{completed['plan_id']}").status_code == 404
    assert client.get(f"/api/v1/runs/{run.json()['id']}").status_code == 404
