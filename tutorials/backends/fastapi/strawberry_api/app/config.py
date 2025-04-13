import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    postgres_url: str = "postgresql+asyncpg://user:pass@localhost/supplychain"
    sqlite_url: str = "sqlite+aiosqlite:///./supplychain.db"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_pass: str = "test"

    class Config:
        env_file = ".env"

settings = Settings()
