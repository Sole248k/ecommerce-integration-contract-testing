import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime
from .database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(64), unique=True, index=True, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "price": self.price,
            "stock": self.stock,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
