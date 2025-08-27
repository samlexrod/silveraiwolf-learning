#!/usr/bin/env python3
"""
Database initialization script for the Supply Chain GraphQL API.
Run this script to create all necessary database tables and sample data.
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base
# Import models to register them with Base metadata
from app.models.product import ProductModel
from app.models.supplier import SupplierModel
from app.models.inventory import InventoryModel

# Load environment variables from .env file
load_dotenv()

def get_database_url():
    """Get database URL from environment variables."""
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pass")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "supplychain")
    return f"postgresql+asyncpg://user:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"

# Build database URL from environment variables
DATABASE_URL = get_database_url()

async def init_database():
    """Initialize the database with all tables and sample data."""
    print("Creating database engine...")
    engine = create_async_engine(get_database_url(), echo=True)
    
    print("Creating database tables...")
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database tables created successfully!")
    
    # Create session for inserting sample data
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("Inserting sample data...")
    async with async_session() as session:
        # Create sample products with prices
        product1 = ProductModel(name="Widget", description="Basic widget for everyday use", price=19.99)
        product2 = ProductModel(name="Gadget", description="Advanced gadget with premium features", price=89.99)
        product3 = ProductModel(name="Tool", description="Essential tool for professionals", price=45.50)
        product4 = ProductModel(name="Device", description="Smart device with IoT capabilities", price=199.99)
        
        session.add_all([product1, product2, product3, product4])
        await session.flush()  # Flush to get IDs
        
        # Create sample suppliers
        supplier1 = SupplierModel(name="Acme Corp")
        supplier2 = SupplierModel(name="Tech Solutions Inc")
        supplier3 = SupplierModel(name="Global Supplies Ltd")
        
        session.add_all([supplier1, supplier2, supplier3])
        await session.flush()
        
        # Create supplier-product relationships using the association table
        from app.models.supplier import supplier_products
        
        # Add relationships to the association table
        await session.execute(
            supplier_products.insert().values([
                {"supplier_id": supplier1.id, "product_id": product1.id},
                {"supplier_id": supplier1.id, "product_id": product2.id},
                {"supplier_id": supplier2.id, "product_id": product2.id},
                {"supplier_id": supplier2.id, "product_id": product3.id},
                {"supplier_id": supplier3.id, "product_id": product3.id},
                {"supplier_id": supplier3.id, "product_id": product4.id},
            ])
        )
        
        # Create sample inventory
        inventory1 = InventoryModel(product_id=product1.id, quantity=100)
        inventory2 = InventoryModel(product_id=product2.id, quantity=50)
        inventory3 = InventoryModel(product_id=product3.id, quantity=75)
        inventory4 = InventoryModel(product_id=product4.id, quantity=25)
        
        session.add_all([inventory1, inventory2, inventory3, inventory4])
        
        await session.commit()
    
    print("Sample data inserted successfully!")
    await engine.dispose()

if __name__ == "__main__":
    print("Initializing Supply Chain GraphQL API database...")
    asyncio.run(init_database())
    print("Database initialization complete!")
