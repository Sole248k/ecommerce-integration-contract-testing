import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

from product_service.app.models import Product
from product_service.app.schemas import (
    ProductCreate,
    ProductResponse,
    StockDeductRequest,
    StockDeductResponse,
)
from product_service.app.routes import (
    create_product,
    list_products,
    get_product,
    deduct_stock,
)

# ==============================================================================
# 1. Schema Validation Unit Tests
# ==============================================================================
def test_product_create_schema_valid():
    """Unit: ProductCreate accepts valid inputs."""
    payload = ProductCreate(name="Mechanical Keyboard", price=89.99, stock=15)
    assert payload.name == "Mechanical Keyboard"
    assert payload.price == 89.99
    assert payload.stock == 15

def test_product_create_schema_negative_price():
    """Unit: ProductCreate rejects negative or zero price."""
    with pytest.raises(ValidationError):
        ProductCreate(name="Invalid Product", price=-5.0, stock=10)

    with pytest.raises(ValidationError):
        ProductCreate(name="Zero Price Product", price=0.0, stock=10)

def test_product_create_schema_negative_stock():
    """Unit: ProductCreate rejects negative stock."""
    with pytest.raises(ValidationError):
        ProductCreate(name="Invalid Stock", price=25.0, stock=-1)

def test_stock_deduct_schema_validation():
    """Unit: StockDeductRequest validates quantity must be > 0."""
    valid = StockDeductRequest(quantity=5)
    assert valid.quantity == 5

    with pytest.raises(ValidationError):
        StockDeductRequest(quantity=0)

    with pytest.raises(ValidationError):
        StockDeductRequest(quantity=-3)

# ==============================================================================
# 2. Model Serialization Unit Tests
# ==============================================================================
def test_product_model_to_dict():
    """Unit: Product.to_dict() serializes attributes properly."""
    prod = Product(
        id="prod_99",
        name="Wireless Mouse",
        sku="SKU-MS-99",
        price=29.99,
        stock=12
    )
    data = prod.to_dict()
    assert data["id"] == "prod_99"
    assert data["name"] == "Wireless Mouse"
    assert data["sku"] == "SKU-MS-99"
    assert data["price"] == 29.99
    assert data["stock"] == 12

# ==============================================================================
# 3. Route & Business Logic Unit Tests (Isolated with Mocked DB Session)
# ==============================================================================
def test_unit_create_product_success():
    """Unit: create_product creates and commits entity."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    payload = ProductCreate(id="p101", name="Monitor", sku="SKU-MN-1", price=300.0, stock=5)
    result = create_product(payload, db=mock_db)

    assert result.id == "p101"
    assert result.name == "Monitor"
    assert mock_db.add.called
    assert mock_db.commit.called
    assert mock_db.refresh.called

def test_unit_create_product_conflict_id():
    """Unit: create_product raises 409 Conflict if ID already exists."""
    mock_db = MagicMock()
    existing_prod = Product(id="p101", name="Existing", sku="SKU-EX", price=10.0, stock=1)
    mock_db.query.return_value.filter.return_value.first.return_value = existing_prod

    payload = ProductCreate(id="p101", name="Monitor", sku="SKU-NEW", price=300.0, stock=5)
    with pytest.raises(HTTPException) as exc_info:
        create_product(payload, db=mock_db)

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail

def test_unit_create_product_conflict_sku():
    """Unit: create_product raises 409 Conflict if SKU already exists."""
    mock_db = MagicMock()
    # First query for ID returns None, second query for SKU returns an existing product
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None,
        Product(id="other", name="Other", sku="SKU-DUPE", price=10.0, stock=1)
    ]

    payload = ProductCreate(id="p_unique", name="Monitor", sku="SKU-DUPE", price=300.0, stock=5)
    with pytest.raises(HTTPException) as exc_info:
        create_product(payload, db=mock_db)

    assert exc_info.value.status_code == 409
    assert "SKU SKU-DUPE already exists" in exc_info.value.detail

def test_unit_get_product_success():
    """Unit: get_product returns existing product."""
    mock_db = MagicMock()
    mock_prod = Product(id="101", name="Keyboard", sku="SKU-KB", price=89.99, stock=10)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_prod

    result = get_product("101", db=mock_db)
    assert result.id == "101"
    assert result.name == "Keyboard"

def test_unit_get_product_not_found():
    """Unit: get_product raises 404 when product is missing."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        get_product("999", db=mock_db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Product not found"

def test_unit_deduct_stock_success():
    """Unit: deduct_stock reduces stock and returns updated state."""
    mock_db = MagicMock()
    prod = Product(id="101", name="Keyboard", sku="SKU-KB", price=89.99, stock=15)
    mock_db.query.return_value.filter.return_value.first.return_value = prod

    req = StockDeductRequest(quantity=3)
    response = deduct_stock("101", req, db=mock_db)

    assert response.remaining_stock == 12
    assert response.status == "DEDUCTED"
    assert prod.stock == 12
    assert mock_db.commit.called

def test_unit_deduct_stock_insufficient():
    """Unit: deduct_stock raises 409 Conflict if stock is insufficient."""
    mock_db = MagicMock()
    prod = Product(id="101", name="Keyboard", sku="SKU-KB", price=89.99, stock=2)
    mock_db.query.return_value.filter.return_value.first.return_value = prod

    req = StockDeductRequest(quantity=5)
    with pytest.raises(HTTPException) as exc_info:
        deduct_stock("101", req, db=mock_db)

    assert exc_info.value.status_code == 409
    assert "Insufficient stock available" in exc_info.value.detail
    assert prod.stock == 2 # unchanged
