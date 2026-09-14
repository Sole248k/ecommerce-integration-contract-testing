from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ProductCreate(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    sku: Optional[str] = None
    price: float = Field(..., gt=0, description="Product price must be greater than 0")
    stock: int = Field(default=0, ge=0, description="Initial stock must be non-negative")

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sku: str
    price: float
    stock: int
    created_at: Optional[datetime] = None

class StockDeductRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity to deduct must be greater than 0")

class StockDeductResponse(BaseModel):
    id: str
    remaining_stock: int
    status: str
