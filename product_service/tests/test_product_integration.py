import pytest
from product_service.app.models import Product

def test_it_01_create_product_positive(client, db_session):
    """
    IT-01: Create New Product (Positive)
    Preconditions: Clean DB session.
    Input: Valid product payload {name: "Gaming Laptop", price: 999.99, stock: 10}
    Expected: 201 Created, entity persisted in database.
    """
    payload = {
        "name": "Gaming Laptop",
        "price": 999.99,
        "stock": 10,
        "sku": "SKU-LAPTOP-01"
    }

    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["name"] == "Gaming Laptop"
    assert data["price"] == 999.99
    assert data["stock"] == 10
    assert data["sku"] == "SKU-LAPTOP-01"
    assert "id" in data and len(data["id"]) > 0

    # Verify direct database persistence (Integration verification)
    persisted = db_session.query(Product).filter(Product.id == data["id"]).first()
    assert persisted is not None, "Entity was not persisted to the database!"
    assert persisted.name == "Gaming Laptop"
    assert persisted.stock == 10

def test_it_02_create_product_invalid_payload_negative(client, db_session):
    """
    IT-02: Create Product with Invalid Payload (Negative)
    Preconditions: Clean DB session.
    Input: Payload with negative price (price: -5.0) violating validation constraints.
    Expected: 422 Unprocessable Entity; DB state remains unchanged.
    """
    initial_count = db_session.query(Product).count()

    invalid_payload = {
        "name": "Defective Widget",
        "price": -5.0,  # Invalid: price must be > 0
        "stock": 5
    }

    response = client.post("/api/v1/products", json=invalid_payload)
    assert response.status_code == 422, f"Expected 422 Unprocessable Entity, got {response.status_code}"

    # Verify DB state did not change
    current_count = db_session.query(Product).count()
    assert current_count == initial_count, "Database state was modified despite validation failure!"

def test_it_product_deduct_stock_and_get(client, db_session):
    """
    Supplemental Integration Test: Verify stock deduction and catalog retrieval.
    """
    # Create product directly
    prod = Product(id="prod-test-01", name="Wireless Mouse", sku="SKU-WM-01", price=29.99, stock=8)
    db_session.add(prod)
    db_session.commit()

    # Get product via API
    get_res = client.get("/api/v1/products/prod-test-01")
    assert get_res.status_code == 200
    assert get_res.json()["stock"] == 8

    # Deduct stock
    deduct_res = client.patch("/api/v1/products/prod-test-01/deduct-stock", json={"quantity": 3})
    assert deduct_res.status_code == 200
    assert deduct_res.json()["remaining_stock"] == 5

    # Verify insufficient stock rejection
    excess_res = client.patch("/api/v1/products/prod-test-01/deduct-stock", json={"quantity": 10})
    assert excess_res.status_code == 409
    assert "Insufficient stock" in excess_res.json()["detail"]
