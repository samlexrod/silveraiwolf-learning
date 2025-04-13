from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# Load from env or hardcode for dev
DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql+asyncpg://user:pass@localhost/supplychain")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_pg_session() -> AsyncSession:
    async with async_session() as session:
        yield session
