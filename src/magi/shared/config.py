from functools import lru_cache

from pydantic import Field, SecretStr
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
    object_storage_endpoint: str = "localhost:9000"
    object_storage_access_key: str = "magi"
    object_storage_secret_key: SecretStr = SecretStr("magi-minio-secret")
    object_storage_bucket: str = "magi-sources"
    object_storage_secure: bool = False
    object_storage_timeout_seconds: float = Field(default=10.0, gt=0)


class EmbeddingSettings(BaseSettings):
    """Required environment configuration for the embedding adapter."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MAGI_EMBEDDING_",
        extra="ignore",
    )

    base_url: str
    model_id: str
    model_revision: str
    vector_dimension: int = Field(ge=1)
    batch_size: int = Field(ge=1)
    timeout_seconds: float = Field(gt=0)
    api_key: SecretStr | None = None


class QdrantSettings(BaseSettings):
    """Required environment configuration for the Qdrant adapter."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MAGI_QDRANT_",
        extra="ignore",
    )

    url: str
    collection: str
    vector_dimension: int = Field(ge=1)
    batch_size: int = Field(ge=1)
    timeout_seconds: float = Field(gt=0)
    api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
