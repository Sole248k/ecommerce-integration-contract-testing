import os
from pathlib import Path
import pytest
import httpx
import pact
from order_service.app.product_client import ProductClient

PACT_DIR = Path(__file__).resolve().parent.parent.parent / "pacts"

def test_pact_consumer_contracts():
    """
    Task 2: Consumer-Driven Contract Testing (Consumer Phase)
    Defines 4 contracts required for Order Service -> Product Service communication:
    1. GET /api/v1/products/101 -> 200 OK (Product Details)
    2. GET /api/v1/products/999 -> 404 Not Found
    3. PATCH /api/v1/products/101/deduct-stock -> 200 OK (Stock Deducted)
    4. PATCH /api/v1/products/102/deduct-stock -> 409 Conflict (Insufficient Stock)
    """
    consumer = pact.Pact("order_service", "product_service")

    # Contract 1: Retrieve Existing Product
    (
        consumer.upon_receiving("a request for existing product with ID 101")
        .given("Product with ID 101 exists in catalog")
        .with_request("GET", "/api/v1/products/101")
        .will_respond_with(200)
        .with_body(
            {
                "id": "101",
                "name": "Mechanical Keyboard",
                "price": 89.99,
                "stock": 15
            },
            "application/json"
        )
    )

    # Contract 2: Product Not Found
    (
        consumer.upon_receiving("a request for product with ID 999 which does not exist")
        .given("Product with ID 999 does not exist")
        .with_request("GET", "/api/v1/products/999")
        .will_respond_with(404)
        .with_body(
            {"detail": "Product not found"},
            "application/json"
        )
    )

    # Contract 3: Deduct Product Stock (Fulfillment)
    (
        consumer.upon_receiving("a request to deduct 2 units of stock from product 101")
        .given("Product 101 has 15 units of stock")
        .with_request("PATCH", "/api/v1/products/101/deduct-stock")
        .with_header("Content-Type", "application/json")
        .with_body({"quantity": 2}, "application/json")
        .will_respond_with(200)
        .with_body(
            {
                "id": "101",
                "remaining_stock": 13,
                "status": "DEDUCTED"
            },
            "application/json"
        )
    )

    # Contract 4: Out-of-Stock Insufficient Inventory
    (
        consumer.upon_receiving("a request to deduct stock when product 102 has 0 inventory")
        .given("Product 102 has 0 inventory")
        .with_request("PATCH", "/api/v1/products/102/deduct-stock")
        .with_header("Content-Type", "application/json")
        .with_body({"quantity": 1}, "application/json")
        .will_respond_with(409)
        .with_body(
            {"detail": "Insufficient stock available"},
            "application/json"
        )
    )

    # Execute consumer interactions against the Pact Mock Server
    print(f"\n[PACT] Starting Pact Mock Server on dynamic port...")
    with consumer.serve() as mock_server:
        print(f"[PACT] Mock Server active at: {mock_server.url}")
        client = ProductClient(base_url=str(mock_server.url))

        # 1. Test GET /api/v1/products/101
        prod_101 = client.get_product("101")
        assert prod_101["id"] == "101"
        assert prod_101["name"] == "Mechanical Keyboard"
        assert prod_101["price"] == 89.99
        assert prod_101["stock"] == 15
        print("[PACT] Contract 1 (Retrieve Existing Product): PASSED")

        # 2. Test GET /api/v1/products/999 (Expect 404)
        from fastapi import HTTPException
        try:
            client.get_product("999")
            pytest.fail("Expected 404 for non-existent product 999")
        except HTTPException as exc:
            assert exc.status_code == 404
            assert "not found" in exc.detail.lower()
        print("[PACT] Contract 2 (Product Not Found): PASSED")

        # 3. Test PATCH /api/v1/products/101/deduct-stock
        deduct_res = client.deduct_stock("101", 2)
        assert deduct_res["id"] == "101"
        assert deduct_res["remaining_stock"] == 13
        assert deduct_res["status"] == "DEDUCTED"
        print("[PACT] Contract 3 (Deduct Stock): PASSED")

        # 4. Test PATCH /api/v1/products/102/deduct-stock (Expect 409)
        try:
            client.deduct_stock("102", 1)
            pytest.fail("Expected 409 Conflict for out-of-stock product 102")
        except HTTPException as exc:
            assert exc.status_code == 409
            assert "insufficient stock" in exc.detail.lower()
        print("[PACT] Contract 4 (Insufficient Stock): PASSED")

    # Write generated contract file
    PACT_DIR.mkdir(parents=True, exist_ok=True)
    consumer.write_file(str(PACT_DIR), overwrite=True)
    print(f"\n[PACT] Contract JSON file generated at: {PACT_DIR / 'order_service-product_service.json'}")
    assert (PACT_DIR / "order_service-product_service.json").exists()
