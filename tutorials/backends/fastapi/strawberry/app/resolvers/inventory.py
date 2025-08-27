import strawberry
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.inventory import Inventory, InventoryModel
from app.models.product import Product, ProductModel
from app.db.postgres import get_pg_session

@strawberry.type
class Query:
    @strawberry.field
    async def get_inventory(self) -> List[Inventory]:
        session = await get_pg_session()
        async with session:
            # Use SQLAlchemy ORM with eager loading of product
            stmt = (
                select(InventoryModel)
                .options(selectinload(InventoryModel.product))
                .order_by(InventoryModel.product_id)
            )
            result = await session.execute(stmt)
            inventory_items = result.scalars().all()
            
            # Convert SQLAlchemy models to GraphQL types
            return [
                Inventory(
                    product=Product(
                    id=item.product.id, 
                    name=item.product.name, 
                    description=item.product.description,
                    price=item.product.price
                ),
                    quantity=item.quantity
                ) for item in inventory_items
            ]
