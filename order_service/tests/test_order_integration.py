import pytest
from order_service.app.models import Order, OrderItem

def test_it_03_place_order_positive(client, db_session):
    """
    IT-03: Place a New Order (Positive)
    Preconditions: Upstream Product Service confirms P101 exists at $50.00, stock=10.
    Input: {customer_id: "cust_100", items: [{product_id: "P101", quantity: 2}]}
    Expected: 201 Created, total_amount=100.00, status="PENDING", persisted in DB.
    """
    payload = {
        "customer_id": "cust_100",
        "items": [
            {"product_id": "P101", "quantity": 2}
        ]
    }

    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["customer_id"] == "cust_100"
    assert data["total_amount"] == 100.00
    assert data["status"] == "PENDING"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == "P101"
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["unit_price"] == 50.00

    order_id = data["id"]

    # Direct database verification (Integration validation)
    persisted_order = db_session.query(Order).filter(Order.id == order_id).first()
    assert persisted_order is not None, "Order was not persisted to PostgreSQL database!"
    assert persisted_order.total_amount == 100.00
    assert persisted_order.status == "PENDING"
    assert len(persisted_order.items) == 1
    assert persisted_order.items[0].quantity == 2

def test_it_04_place_order_non_existent_product_negative(client, db_session):
    """
    IT-04: Place Order for Non-Existent Product (Negative)
    Preconditions: Upstream Product Service returns 404 for product P999.
    Input: {customer_id: "cust_200", items: [{product_id: "P999", quantity: 1}]}
    Expected: 404 Not Found (or 400 Bad Request); DB state remains unchanged.
    """
    initial_orders_count = db_session.query(Order).count()

    invalid_payload = {
        "customer_id": "cust_200",
        "items": [
            {"product_id": "P999", "quantity": 1}
        ]
    }

    response = client.post("/api/v1/orders", json=invalid_payload)
    assert response.status_code in [400, 404], f"Expected 404 or 400, got {response.status_code}: {response.text}"

    # Verify no order was committed
    current_count = db_session.query(Order).count()
    assert current_count == initial_orders_count, "An order was erroneously saved to DB!"

def test_it_05_update_existing_order_status_positive(client, db_session, mock_product_client):
    """
    IT-05: Update Existing Order Status (Positive)
    Preconditions: Order exists in DB with status "PENDING".
    Input: PATCH /api/v1/orders/{id} with {"status": "CONFIRMED"}
    Expected: 200 OK, status transitions to "CONFIRMED" in database.
    """
    # 1. Create order
    create_res = client.post("/api/v1/orders", json={
        "customer_id": "cust_300",
        "items": [{"product_id": "P101", "quantity": 1}]
    })
    assert create_res.status_code == 201
    order_id = create_res.json()["id"]

    # 2. Update status to CONFIRMED
    update_res = client.patch(f"/api/v1/orders/{order_id}", json={"status": "CONFIRMED"})
    assert update_res.status_code == 200, f"Expected 200 OK, got {update_res.status_code}"
    
    updated_data = update_res.json()
    assert updated_data["status"] == "CONFIRMED"

    # 3. Direct DB verification
    persisted = db_session.query(Order).filter(Order.id == order_id).first()
    assert persisted is not None
    assert persisted.status == "CONFIRMED"

    # Verify deduction was triggered on Product Service client
    assert ("P101", 1) in mock_product_client.deductions
