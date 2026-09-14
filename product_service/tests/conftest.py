import os
os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from product_service.app.database import Base, get_db
from product_service.app.main import app

@pytest.fixture(scope="session")
def postgres_container():
    """Spin up an ephemeral PostgreSQL container via Testcontainers."""
    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError:
        from testcontainers.postgres import PostgresContainer

    print("\n[TDM] Starting dynamic PostgreSQL 16 Testcontainer on Docker...")
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    connection_url = container.get_connection_url()
    print(f"[TDM] Real PostgreSQL Docker Container started successfully: {connection_url}")
    try:
        yield connection_url
    finally:
        print("\n[TDM] Terminating ephemeral PostgreSQL container...")
        try:
            container.stop()
            print("[TDM] Container terminated and cleaned up.")
        except Exception as stop_err:
            print(f"[TDM] Container stop warning: {stop_err}")

@pytest.fixture(scope="session")
def test_engine(postgres_container):
    """Session-level SQLAlchemy engine connected to ephemeral test DB."""
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

@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with DB dependency overridden to the isolated session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
