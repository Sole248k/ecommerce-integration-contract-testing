from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import router as product_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Product Service",
    version="1.0.0",
    description="Product Catalog and Inventory Microservice (Provider)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product_router)

@app.get("/health")
def health_check():
    return {"status": "UP", "service": "product-service"}
