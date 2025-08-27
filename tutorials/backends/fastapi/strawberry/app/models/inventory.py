from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
import strawberry
from typing import Optional

from app.models import Base
from app.models.product import Product

# SQLAlchemy model
class InventoryModel(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)

    product = relationship("ProductModel")

# Strawberry GraphQL type
@strawberry.type
class Inventory:
    product: Product
    quantity: int
    
    @strawberry.field
    def total_value(self) -> float:
        """Calculate total inventory value (quantity × price)."""
        return self.quantity * self.product.price
    
    @strawberry.field
    def total_value_formatted(self) -> str:
        """Calculate formatted total inventory value."""
        total = self.quantity * self.product.price
        return f"${total:.2f}"
    
    @strawberry.field
    def stock_status(self) -> str:
        """Calculate stock status based on quantity."""
        if self.quantity == 0:
            return "OUT_OF_STOCK"
        elif self.quantity <= 10:
            return "LOW_STOCK"
        else:
            return "IN_STOCK"
    
    @strawberry.field
    def stock_status_description(self) -> str:
        """Get human-readable stock status description."""
        status = self.stock_status
        if status == "OUT_OF_STOCK":
            return "Currently out of stock"
        elif status == "LOW_STOCK":
            return f"Only {self.quantity} units remaining"
        else:
            return f"{self.quantity} units in stock"
    
    @strawberry.field
    def needs_restock(self) -> bool:
        """Calculate if product needs restocking."""
        return self.quantity <= 10
