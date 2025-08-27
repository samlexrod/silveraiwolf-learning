from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment variables."""
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pass")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "supplychain")
    return f"postgresql+asyncpg://user:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"

def get_engine():
    """Get database engine with current environment variables."""
    return create_async_engine(get_database_url(), echo=True)

def get_session():
    """Get session factory with current environment variables."""
    engine = get_engine()
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Create default engine and session factory
engine = get_engine()
async_session = get_session()

async def get_pg_session() -> AsyncSession:
    return async_session()
