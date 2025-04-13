from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import strawberry

from app.models.product import Product

Base = declarative_base()

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
