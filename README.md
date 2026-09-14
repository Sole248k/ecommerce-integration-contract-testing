# ⚡ TestForge | Practical Integration & Contract Testing Suite (Day 25)

Enterprise microservice testing platform showcasing **Practical Integration Testing (Pytest + Testcontainers)**, **Consumer-Driven Contract Testing (Pact Framework)**, and an **Interactive Web Dashboard** with Light/Dark mode.

---

## 🏛️ Architecture Overview

* **Product Service (Provider - Port 8001)**: FastAPI catalog & inventory manager connected to PostgreSQL (Docker port 5434).
* **Order Service (Consumer - Port 8002)**: FastAPI order placement & fulfillment manager connected to PostgreSQL (Docker port 5435), synchronously validating inventory with Product Service.
* **Testcontainers (Docker)**: Ephemeral, throwaway PostgreSQL 16 containers orchestrated dynamically per test session.
* **Pact Framework**: Consumer-driven contract (`pacts/order_service-product_service.json`) verified against provider endpoints.
* **Interactive Web Dashboard**: Live SPA running on port 8000 with real-time catalog management, order fulfillment, and live Pytest runner.

---

## 🚀 Quickstart for Teammates

### 1. Prerequisites
Ensure your development environment has:
* **Python 3.10+** (Tested on Python 3.11 - 3.14)
* **Docker Desktop** (Running and accessible via CLI)
* **Git**

### 2. Clone the Repository
```bash
git clone https://github.com/Sole248k/ecommerce-integration-contract-testing.git
cd "Day 25"
```

### 3. Setup Virtual Environment & Install Dependencies
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start Real PostgreSQL Databases in Docker
Start the persistent PostgreSQL containers for local development and the dashboard:
```bash
docker compose up -d
```
Verify that both containers are running:
```bash
docker ps --filter "name=day25"
```
* `day25-product-db`: Listening on `localhost:5434`
* `day25-order-db`: Listening on `localhost:5435`

---

## 🧪 Running the Test Suite

### Run All 8 Tests (Integration + Pact Contracts)
```bash
python -m pytest -v -s
```

### Run Integration Tests Only (IT-01 to IT-05)
```bash
python -m pytest product_service/tests/test_product_integration.py order_service/tests/test_order_integration.py -v -s
```
*(Testcontainers will dynamically spin up ephemeral PostgreSQL 16 containers on Docker and execute tests with transaction rollback isolation).*

### Run Pact Consumer Test (Generates Contract JSON)
```bash
python -m pytest order_service/tests/test_pact_consumer.py -v -s
```

### Run Pact Provider Verification Test (Validates Provider Compliance)
```bash
python -m pytest product_service/tests/test_pact_provider.py -v -s
```

---

## 🖥️ Launching the Interactive Web Dashboard

Start the unified gateway and dashboard server:
```bash
python dashboard_server.py
```
Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

### Dashboard Features:
* **Light & Dark Mode**: Persistent theme toggle in top right corner.
* **Product Catalog**: Add items, check live stock, and test stock deductions.
* **Order Processing**: Place orders with real-time stock validation and update order status (`PENDING` $\rightarrow$ `CONFIRMED`).
* **Pact Contracts Inspector**: Inspect the 4 interactions and copy the generated contract JSON.
* **Live Test Runner**: Trigger Pytest suites directly from the browser and inspect terminal output.

---

## 📄 Generating the Submission Report

To rebuild the Word submission document (`.docx`):
```bash
python generate_report.py
```
Output: `Practical_Integration_and_Contract_Testing_Day25_Report.docx`

---

## 🤝 Team Collaboration Workflow

When making changes to services, schemas, or tests:

1. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Run Tests Before Committing**:
   ```bash
   python -m pytest -v
   ```
3. **If You Modify API Interfaces**:
   * Update the consumer contract in `order_service/tests/test_pact_consumer.py`.
   * Run the consumer test to update `pacts/order_service-product_service.json`.
   * Update provider state handlers in `product_service/tests/test_pact_provider.py`.
   * Verify provider passes: `pytest product_service/tests/test_pact_provider.py`.
4. **Push & Create Pull Request**:
   ```bash
   git add .
   git commit -m "feat: description of your change"
   git push origin feature/your-feature-name
   ```
