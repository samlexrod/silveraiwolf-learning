from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
import strawberry
from typing import List

from app.models import Base
from app.models.product import Product

# Many-to-many link table
supplier_products = Table(
    "supplier_products",
    Base.metadata,
    Column("supplier_id", Integer, ForeignKey("suppliers.id")),
    Column("product_id", Integer, ForeignKey("products.id")),
)

# SQLAlchemy model
class SupplierModel(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    products = relationship("ProductModel", secondary=supplier_products)

# Strawberry GraphQL type
@strawberry.type
class Supplier:
    id: int
    name: str
    products: List[Product]
