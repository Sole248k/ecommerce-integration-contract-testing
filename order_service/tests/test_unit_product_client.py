import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import httpx

from order_service.app.product_client import ProductClient

@pytest.fixture
def client():
    return ProductClient(base_url="http://mock-product-svc:8001")

# ==============================================================================
# Unit Tests for ProductClient.get_product
# ==============================================================================
def test_get_product_success(client):
    """Unit: get_product returns product JSON on 200 OK."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "101",
        "name": "Mechanical Keyboard",
        "price": 89.99,
        "stock": 15
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        data = client.get_product("101")
        assert data["id"] == "101"
        assert data["price"] == 89.99
        assert data["stock"] == 15

def test_get_product_not_found(client):
    """Unit: get_product raises 404 HTTPException when product doesn't exist."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("httpx.Client.get", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            client.get_product("999")

        assert exc_info.value.status_code == 404
        assert "not found in catalog" in exc_info.value.detail

def test_get_product_server_error(client):
    """Unit: get_product raises upstream status code when server errors."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("httpx.Client.get", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            client.get_product("101")

        assert exc_info.value.status_code == 500
        assert "Product Service error" in exc_info.value.detail

def test_get_product_network_failure(client):
    """Unit: get_product raises 503 when network connection fails."""
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(HTTPException) as exc_info:
            client.get_product("101")

        assert exc_info.value.status_code == 503
        assert "Cannot reach Product Service" in exc_info.value.detail

# ==============================================================================
# Unit Tests for ProductClient.deduct_stock
# ==============================================================================
def test_deduct_stock_success(client):
    """Unit: deduct_stock returns updated stock payload on 200 OK."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "101",
        "remaining_stock": 13,
        "status": "DEDUCTED"
    }

    with patch("httpx.Client.patch", return_value=mock_resp):
        data = client.deduct_stock("101", 2)
        assert data["id"] == "101"
        assert data["remaining_stock"] == 13
        assert data["status"] == "DEDUCTED"

def test_deduct_stock_not_found(client):
    """Unit: deduct_stock raises 404 when product is missing."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("httpx.Client.patch", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            client.deduct_stock("999", 1)

        assert exc_info.value.status_code == 404
        assert "not found for stock deduction" in exc_info.value.detail

def test_deduct_stock_insufficient(client):
    """Unit: deduct_stock raises 409 Conflict when stock is insufficient."""
    mock_resp = MagicMock()
    mock_resp.status_code = 409

    with patch("httpx.Client.patch", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            client.deduct_stock("102", 1)

        assert exc_info.value.status_code == 409
        assert "Insufficient stock available" in exc_info.value.detail

def test_deduct_stock_network_failure(client):
    """Unit: deduct_stock raises 503 when network connection fails."""
    with patch("httpx.Client.patch", side_effect=httpx.ConnectError("Connection timed out")):
        with pytest.raises(HTTPException) as exc_info:
            client.deduct_stock("101", 2)

        assert exc_info.value.status_code == 503
        assert "Cannot reach Product Service" in exc_info.value.detail
