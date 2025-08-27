import strawberry
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product, ProductModel
from app.db.postgres import get_pg_session

@strawberry.type
class Query:
    @strawberry.field
    async def get_products(self) -> List[Product]:
        session = await get_pg_session()
        async with session:
            # Use SQLAlchemy ORM with select statement
            stmt = select(ProductModel).order_by(ProductModel.id)
            result = await session.execute(stmt)
            products = result.scalars().all()
            
            # Convert SQLAlchemy models to GraphQL types
            return [Product(id=p.id, name=p.name, description=p.description, price=p.price) for p in products]
