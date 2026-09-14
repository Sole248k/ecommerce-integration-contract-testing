import os
os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from order_service.app.database import Base, get_db
from order_service.app.main import app
from order_service.app.product_client import ProductClient, get_product_client

@pytest.fixture(scope="session")
def postgres_container():
    """Spin up an ephemeral PostgreSQL container via Testcontainers for Order Service."""
    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:
        from testcontainers.postgres import PostgresContainer

    print("\n[TDM] Starting dynamic PostgreSQL 16 Testcontainer on Docker for Order DB...")
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    connection_url = container.get_connection_url()
    print(f"[TDM] Real Order DB PostgreSQL Container started successfully: {connection_url}")
    try:
        yield connection_url
    finally:
        print("\n[TDM] Terminating ephemeral Order DB container...")
        try:
            container.stop()
            print("[TDM] Order DB Container terminated and cleaned up.")
        except Exception as stop_err:
            print(f"[TDM] Container stop warning: {stop_err}")

@pytest.fixture(scope="session")
def test_engine(postgres_container):
    """Session-level SQLAlchemy engine for Order DB."""
    connect_args = {"check_same_thread": False} if postgres_container.startswith("sqlite") else {}
    engine = create_engine(postgres_container, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Function-level isolated DB session with rollback for clean test state."""
    connection = test_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

class MockProductClient:
    """Mock client stubbing upstream Product Service responses for Integration Testing."""
    def __init__(self):
        self.catalog = {
            "P101": {"id": "P101", "name": "Mechanical Keyboard", "price": 50.00, "stock": 10},
            "p101": {"id": "p101", "name": "Mechanical Keyboard", "price": 49.99, "stock": 10},
            "P102": {"id": "P102", "name": "Out of Stock Keycap", "price": 15.00, "stock": 0},
        }
        self.deductions = []

    def get_product(self, product_id: str) -> dict:
        from fastapi import HTTPException
        if product_id in self.catalog:
            return self.catalog[product_id]
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID '{product_id}' not found in catalog"
        )

    def deduct_stock(self, product_id: str, quantity: int) -> dict:
        from fastapi import HTTPException
        if product_id not in self.catalog:
            raise HTTPException(status_code=404, detail="Product not found")
        item = self.catalog[product_id]
        if item["stock"] < quantity:
            raise HTTPException(status_code=409, detail="Insufficient stock available")
        item["stock"] -= quantity
        self.deductions.append((product_id, quantity))
        return {"id": product_id, "remaining_stock": item["stock"], "status": "DEDUCTED"}

@pytest.fixture(scope="function")
def mock_product_client():
    return MockProductClient()

@pytest.fixture(scope="function")
def client(db_session, mock_product_client):
    """FastAPI TestClient with overridden DB session and ProductClient."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_product_client():
        return mock_product_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_product_client] = override_product_client

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
