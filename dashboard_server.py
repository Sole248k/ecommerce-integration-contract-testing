import os
os.environ["PRODUCT_SERVICE_URL"] = "http://localhost:8000"
import sys
import json
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from product_service.app.database import engine as prod_engine, Base as ProdBase, SessionLocal as ProdSession
from product_service.app.models import Product
from product_service.app.routes import router as product_router

from order_service.app.database import engine as order_engine, Base as OrderBase
from order_service.app.routes import router as order_router

# Initialize databases
ProdBase.metadata.create_all(bind=prod_engine)
OrderBase.metadata.create_all(bind=order_engine)

# Seed demo products if empty
def seed_demo_products():
    db = ProdSession()
    try:
        if db.query(Product).count() == 0:
            demo_items = [
                Product(id="101", name="Mechanical Keyboard RGB", sku="SKU-KB-101", price=89.99, stock=15),
                Product(id="102", name="Ultra-Light Wireless Mouse", sku="SKU-MS-102", price=49.99, stock=8),
                Product(id="103", name="Curved Gaming Monitor 34-inch", sku="SKU-MN-103", price=450.00, stock=4),
                Product(id="104", name="Noise-Canceling Headset", sku="SKU-HS-104", price=129.50, stock=20),
            ]
            db.add_all(demo_items)
            db.commit()
    finally:
        db.close()

seed_demo_products()

app = FastAPI(
    title="TestForge Gateway & Dashboard Server",
    version="1.0.0",
    description="Unified API gateway and testing dashboard for Practical Integration & Contract Testing (Day 25)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from order_service.app.product_client import ProductClient, get_product_client
app.dependency_overrides[get_product_client] = lambda: ProductClient(base_url="http://127.0.0.1:8000")

# Mount Microservice Routers
app.include_router(product_router)
app.include_router(order_router)

# Mount Static Files
DASHBOARD_DIR = Path(__file__).resolve().parent / "dashboard"
PACTS_FILE = Path(__file__).resolve().parent / "pacts" / "order_service-product_service.json"

app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="static")

@app.get("/")
def serve_dashboard():
    return FileResponse(DASHBOARD_DIR / "index.html")

@app.get("/api/contract")
def get_pact_contract():
    if not PACTS_FILE.exists():
        raise HTTPException(status_code=404, detail="Contract file not yet generated.")
    with open(PACTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/tests/run")
def run_tests(suite: str = Query(default="all")):
    """
    Executes test suites via pytest and returns output.
    """
    python_exe = sys.executable
    cmd = [python_exe, "-m", "pytest", "-v"]

    if suite == "integration":
        cmd += [
            "product_service/tests/test_product_integration.py",
            "order_service/tests/test_order_integration.py"
        ]
    elif suite == "consumer":
        cmd += ["order_service/tests/test_pact_consumer.py"]
    elif suite == "provider":
        cmd += ["product_service/tests/test_pact_provider.py"]
    else:  # all
        cmd += [
            "order_service/tests/test_order_integration.py",
            "product_service/tests/test_product_integration.py",
            "order_service/tests/test_pact_consumer.py",
            "product_service/tests/test_pact_provider.py"
        ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(Path(__file__).resolve().parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120
        )
        return {
            "suite": suite,
            "exit_code": result.returncode,
            "output": result.stdout
        }
    except subprocess.TimeoutExpired:
        return {
            "suite": suite,
            "exit_code": -1,
            "output": "Test execution timed out after 120 seconds."
        }
    except Exception as e:
        return {
            "suite": suite,
            "exit_code": -1,
            "output": f"Error executing tests: {str(e)}"
        }

if __name__ == "__main__":
    uvicorn.run("dashboard_server:app", host="127.0.0.1", port=8000, reload=False)
