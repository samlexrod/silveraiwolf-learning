import strawberry
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.supplier import Supplier, SupplierModel
from app.models.product import Product, ProductModel
from app.db.postgres import get_pg_session

@strawberry.type
class Query:
    @strawberry.field
    async def get_suppliers(self) -> List[Supplier]:
        session = await get_pg_session()
        async with session:
            # Use SQLAlchemy ORM with eager loading of products
            stmt = (
                select(SupplierModel)
                .options(selectinload(SupplierModel.products))
                .order_by(SupplierModel.id)
            )
            result = await session.execute(stmt)
            suppliers = result.scalars().all()
            
            # Convert SQLAlchemy models to GraphQL types
            supplier_list = []
            for supplier in suppliers:
                # Convert related products to GraphQL types
                supplier_products = [
                    Product(id=p.id, name=p.name, description=p.description, price=p.price) 
                    for p in supplier.products
                ]
                supplier_list.append(
                    Supplier(id=supplier.id, name=supplier.name, products=supplier_products)
                )
            
            return supplier_list
