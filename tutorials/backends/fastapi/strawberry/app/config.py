import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    postgres_url: str = "postgresql+asyncpg://user:pass@localhost/supplychain"

    class Config:
        env_file = ".env"

settings = Settings()
