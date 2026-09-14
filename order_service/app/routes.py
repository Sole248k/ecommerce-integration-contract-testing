import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Order, OrderItem
from .schemas import OrderCreate, OrderUpdate, OrderResponse
from .product_client import ProductClient, get_product_client

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    prod_client: ProductClient = Depends(get_product_client),
):
    total_amount = 0.0
    items_to_create = []

    # Validate each product against Product Service
    for item in payload.items:
        prod_data = prod_client.get_product(item.product_id)
        if not prod_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {item.product_id} not found"
            )

        avail_stock = prod_data.get("stock", 0)
        if avail_stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product '{item.product_id}'. Available: {avail_stock}, requested: {item.quantity}"
            )

        unit_price = float(prod_data["price"])
        total_amount += round(unit_price * item.quantity, 2)

        items_to_create.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": unit_price,
        })

    order_id = f"ord_{uuid.uuid4().hex[:8]}"
    order = Order(
        id=order_id,
        customer_id=payload.customer_id,
        total_amount=round(total_amount, 2),
        status="PENDING",
    )
    db.add(order)
    db.flush()

    for item_info in items_to_create:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_info["product_id"],
            quantity=item_info["quantity"],
            unit_price=item_info["unit_price"],
        )
        db.add(order_item)

    db.commit()
    db.refresh(order)
    return order

@router.get("", response_model=List[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.created_at.desc()).all()

@router.get("/{id}", response_model=OrderResponse)
def get_order(id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order

@router.patch("/{id}", response_model=OrderResponse)
def update_order_status(
    id: str,
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    prod_client: ProductClient = Depends(get_product_client),
):
    order = db.query(Order).filter(Order.id == id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # If transitioning to CONFIRMED, deduct stock from Product Service
    if payload.status.upper() == "CONFIRMED" and order.status != "CONFIRMED":
        for item in order.items:
            prod_client.deduct_stock(item.product_id, item.quantity)

    order.status = payload.status.upper()
    db.commit()
    db.refresh(order)
    return order
