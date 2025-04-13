from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
import strawberry
from typing import Optional

Base = declarative_base()

# SQLAlchemy model
class ProductModel(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

# Strawberry GraphQL type
@strawberry.type
class Product:
    id: int
    name: str
    description: Optional[str] = None
