from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MAGI_",
        extra="ignore",
    )

    app_name: str = "Magi API"
    environment: str = "development"
    docs_enabled: bool = True
    database_url: str = Field(
        default="postgresql+asyncpg://magi:magi@localhost:5432/magi",
        repr=False,
    )
    database_pool_size: int = Field(default=5, ge=1)
    database_pool_timeout_seconds: float = Field(default=5.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
