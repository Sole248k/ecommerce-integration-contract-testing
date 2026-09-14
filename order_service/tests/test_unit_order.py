import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

from order_service.app.models import Order, OrderItem
from order_service.app.schemas import (
    OrderItemCreate,
    OrderCreate,
    OrderUpdate,
    OrderResponse,
)
from order_service.app.routes import (
    create_order,
    get_order,
    update_order_status,
)

# ==============================================================================
# 1. Schema Validation Unit Tests
# ==============================================================================
def test_order_create_schema_valid():
    """Unit: OrderCreate accepts valid customer and item payloads."""
    payload = OrderCreate(
        customer_id="cust_101",
        items=[
            OrderItemCreate(product_id="p101", quantity=2),
            OrderItemCreate(product_id="p102", quantity=1),
        ]
    )
    assert payload.customer_id == "cust_101"
    assert len(payload.items) == 2
    assert payload.items[0].quantity == 2

def test_order_create_schema_empty_items():
    """Unit: OrderCreate rejects empty items list."""
    with pytest.raises(ValidationError):
        OrderCreate(customer_id="cust_101", items=[])

def test_order_item_negative_quantity():
    """Unit: OrderItemCreate rejects negative or zero quantity."""
    with pytest.raises(ValidationError):
        OrderItemCreate(product_id="p101", quantity=0)

    with pytest.raises(ValidationError):
        OrderItemCreate(product_id="p101", quantity=-2)

# ==============================================================================
# 2. Model Serialization Unit Tests
# ==============================================================================
def test_order_models_to_dict():
    """Unit: Order and OrderItem to_dict() serialization."""
    order = Order(
        id="ord_test_01",
        customer_id="cust_alice",
        total_amount=150.00,
        status="PENDING"
    )
    item = OrderItem(
        id=1,
        order_id="ord_test_01",
        product_id="prod_keyboard",
        quantity=1,
        unit_price=150.00,
        order=order
    )

    data = order.to_dict()
    assert data["id"] == "ord_test_01"
    assert data["customer_id"] == "cust_alice"
    assert data["total_amount"] == 150.00
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == "prod_keyboard"

# ==============================================================================
# 3. Route & Business Logic Unit Tests (Isolated with Mocked DB and Mocked Client)
# ==============================================================================
def test_unit_create_order_success():
    """Unit: create_order validates stock, computes total, and adds Order to DB."""
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.get_product.return_value = {
        "id": "p101",
        "name": "Keyboard",
        "price": 50.00,
        "stock": 10
    }

    payload = OrderCreate(
        customer_id="cust_bob",
        items=[OrderItemCreate(product_id="p101", quantity=2)]
    )

    result = create_order(payload, db=mock_db, prod_client=mock_client)

    assert result.customer_id == "cust_bob"
    assert result.total_amount == 100.00
    assert result.status == "PENDING"
    mock_client.get_product.assert_called_with("p101")
    assert mock_db.add.called
    assert mock_db.commit.called

def test_unit_create_order_insufficient_stock():
    """Unit: create_order rejects when requested quantity exceeds available stock."""
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_client.get_product.return_value = {
        "id": "p101",
        "name": "Keyboard",
        "price": 50.00,
        "stock": 1 # Only 1 in stock
    }

    payload = OrderCreate(
        customer_id="cust_bob",
        items=[OrderItemCreate(product_id="p101", quantity=5)] # Requests 5
    )

    with pytest.raises(HTTPException) as exc_info:
        create_order(payload, db=mock_db, prod_client=mock_client)

    assert exc_info.value.status_code == 400
    assert "Insufficient stock" in exc_info.value.detail

def test_unit_get_order_not_found():
    """Unit: get_order raises 404 when order ID does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        get_order("ord_non_existent", db=mock_db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Order not found"

def test_unit_update_order_status_confirmed_deducts_stock():
    """Unit: update_order_status to CONFIRMED triggers deduct_stock for line items."""
    mock_db = MagicMock()
    mock_client = MagicMock()

    order = Order(
        id="ord_100",
        customer_id="cust_dan",
        total_amount=100.0,
        status="PENDING"
    )
    item = OrderItem(order_id="ord_100", product_id="p101", quantity=2, unit_price=50.0)
    order.items.append(item)
    mock_db.query.return_value.filter.return_value.first.return_value = order

    update_payload = OrderUpdate(status="CONFIRMED")
    result = update_order_status("ord_100", update_payload, db=mock_db, prod_client=mock_client)

    assert result.status == "CONFIRMED"
    mock_client.deduct_stock.assert_called_once_with("p101", 2)
    assert mock_db.commit.called

def test_unit_update_order_not_found():
    """Unit: update_order_status raises 404 when order does not exist."""
    mock_db = MagicMock()
    mock_client = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        update_order_status("ord_999", OrderUpdate(status="CONFIRMED"), db=mock_db, prod_client=mock_client)

    assert exc_info.value.status_code == 404
