from sqlalchemy import Column, Integer, String, Float
import strawberry
from typing import Optional
from app.models import Base

# SQLAlchemy model
class ProductModel(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False, default=0.0)

# Strawberry GraphQL type
@strawberry.type
class Product:
    id: int
    name: str
    description: Optional[str] = None
    price: float = 0.0
    
    @strawberry.field
    def price_formatted(self) -> str:
        """Calculate formatted price with currency symbol."""
        return f"${self.price:.2f}"
    
    @strawberry.field
    def is_premium(self) -> bool:
        """Calculate if product is premium (price > $50)."""
        return self.price > 50.0
