from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import router as order_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Order Service",
    version="1.0.0",
    description="Order Processing Microservice (Consumer)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(order_router)

@app.get("/health")
def health_check():
    return {"status": "UP", "service": "order-service"}
