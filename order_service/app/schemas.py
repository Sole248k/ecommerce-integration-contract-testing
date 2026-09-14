from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")

class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    product_id: str
    quantity: int
    unit_price: float

class OrderCreate(BaseModel):
    customer_id: str = Field(..., min_length=1)
    items: List[OrderItemCreate] = Field(..., min_length=1)

class OrderUpdate(BaseModel):
    status: str = Field(..., min_length=1)

class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    total_amount: float
    status: str
    created_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
