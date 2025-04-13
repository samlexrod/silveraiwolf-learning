from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

SQLITE_URL = "sqlite+aiosqlite:///./supplychain.db"

engine = create_async_engine(SQLITE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_sqlite_session() -> AsyncSession:
    async with async_session() as session:
        yield session
