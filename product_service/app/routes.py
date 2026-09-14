import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Product
from .schemas import (
    ProductCreate,
    ProductResponse,
    StockDeductRequest,
    StockDeductResponse,
)

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    prod_id = payload.id or str(uuid.uuid4())
    sku = payload.sku or f"SKU-{prod_id[:8].upper()}"

    # Check if ID already exists
    existing = db.query(Product).filter(Product.id == prod_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with ID {prod_id} already exists"
        )

    # Check if SKU already exists
    existing_sku = db.query(Product).filter(Product.sku == sku).first()
    if existing_sku:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU {sku} already exists"
        )

    product = Product(
        id=prod_id,
        name=payload.name,
        sku=sku,
        price=payload.price,
        stock=payload.stock,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.created_at.desc()).all()

@router.get("/{id}", response_model=ProductResponse)
def get_product(id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product

@router.patch("/{id}/deduct-stock", response_model=StockDeductResponse)
def deduct_stock(id: str, payload: StockDeductRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if product.stock < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient stock available"
        )

    product.stock -= payload.quantity
    db.commit()
    db.refresh(product)

    return StockDeductResponse(
        id=product.id,
        remaining_stock=product.stock,
        status="DEDUCTED"
    )
