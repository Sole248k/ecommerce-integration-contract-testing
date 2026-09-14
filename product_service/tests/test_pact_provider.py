import os
import time
import socket
import threading
from pathlib import Path
import pytest
import uvicorn
import pact

from product_service.app.main import app
from product_service.app.database import SessionLocal, engine, Base
from product_service.app.models import Product

PACT_FILE = Path(__file__).resolve().parent.parent.parent / "pacts" / "order_service-product_service.json"

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def state_handler(state: str, **kwargs):
    """
    Provider state handler: seeds or clears database state before Pact verification replays each interaction.
    """
    print(f"\n[PACT PROVIDER STATE] Handling state: '{state}'")
    db = SessionLocal()
    try:
        if "Product with ID 101 exists in catalog" in state or "Product 101 has 15 units of stock" in state:
            prod = db.query(Product).filter(Product.id == "101").first()
            if not prod:
                prod = Product(id="101", name="Mechanical Keyboard", sku="SKU-KB-101", price=89.99, stock=15)
                db.add(prod)
            else:
                prod.name = "Mechanical Keyboard"
                prod.price = 89.99
                prod.stock = 15
            db.commit()

        elif "Product with ID 999 does not exist" in state:
            db.query(Product).filter(Product.id == "999").delete()
            db.commit()

        elif "Product 102 has 0 inventory" in state:
            prod = db.query(Product).filter(Product.id == "102").first()
            if not prod:
                prod = Product(id="102", name="Out of Stock Item", sku="SKU-KB-102", price=49.99, stock=0)
                db.add(prod)
            else:
                prod.stock = 0
            db.commit()
    finally:
        db.close()

def test_pact_provider_verification():
    """
    Task 2: Consumer-Driven Contract Testing (Provider Verification Phase)
    Replays all interactions in order_service-product_service.json against the live Product Service.
    """
    assert PACT_FILE.exists(), f"Pact contract file not found at {PACT_FILE}. Run test_pact_consumer.py first!"

    Base.metadata.create_all(bind=engine)

    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to become responsive
    time.sleep(1.0)
    provider_url = f"http://localhost:{port}"
    print(f"\n[PACT PROVIDER] Live Product Service running at {provider_url}")

    try:
        verifier = pact.Verifier("product_service")
        verifier.add_source(str(PACT_FILE))
        verifier.add_transport(url=provider_url)
        verifier.state_handler(state_handler)
        
        print("\n[PACT PROVIDER] Executing contract verification against Product Service...")
        verifier.verify()
        print("[PACT PROVIDER] Contract verification SUCCESSFUL! Provider honors all consumer expectations.")
    finally:
        server.should_exit = True
