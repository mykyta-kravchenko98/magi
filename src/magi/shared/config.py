from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Literal, cast

import boto3
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from mypy_boto3_secretsmanager import SecretsManagerClient


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MAGI_",
        extra="ignore",
    )

    app_name: str = "Magi API"
    environment: Literal["development", "test", "production"] = "development"
    docs_enabled: bool = True
    max_upload_bytes: int = Field(default=20 * 1_024 * 1_024, ge=1)
    chunk_target_tokens: int = Field(default=600, ge=1)
    chunk_soft_max_tokens: int = Field(default=800, ge=1)
    chunk_hard_max_tokens: int = Field(default=1_000, ge=1)
    chunk_overlap_tokens: int = Field(default=80, ge=0)
    embedding_input_max_tokens: int = Field(default=2_048, ge=1)
    database_url: str = Field(
        default="postgresql+asyncpg://localhost/magi",
        repr=False,
    )
    database_pool_size: int = Field(default=5, ge=1)
    database_pool_timeout_seconds: float = Field(default=5.0, gt=0)
    object_storage_endpoint: str = "localhost:9000"
    object_storage_access_key: str = ""
    object_storage_secret_key: SecretStr = SecretStr("")
    object_storage_bucket: str = "magi-sources"
    object_storage_secure: bool = False
    object_storage_timeout_seconds: float = Field(default=10.0, gt=0)

    @model_validator(mode="after")
    def validate_consistent_limits(self) -> Settings:
        if not (
            self.chunk_target_tokens
            <= self.chunk_soft_max_tokens
            <= self.chunk_hard_max_tokens
            <= self.embedding_input_max_tokens
        ):
            raise ValueError(
                "chunk limits must satisfy target <= soft max <= hard max <= embedding input max"
            )
        if self.chunk_overlap_tokens >= self.chunk_target_tokens:
            raise ValueError("chunk overlap must be smaller than the target")
        if self.environment == "production":
            missing = {
                "database_url",
                "object_storage_access_key",
                "object_storage_secret_key",
            } - self.model_fields_set
            if missing:
                names = ", ".join(sorted(f"MAGI_{name.upper()}" for name in missing))
                raise ValueError(f"production requires explicit settings: {names}")
            if self.docs_enabled:
                raise ValueError("MAGI_DOCS_ENABLED must be false in production")
        return self


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
    api_key: SecretStr


@lru_cache
def load_secrets_manager_environment() -> None:
    """Overlay missing MAGI_* variables from an optional Secrets Manager JSON secret.

    Explicit environment variables always win. AWS credentials are resolved by boto3's
    standard chain, so this works with a local profile, container credentials, or OIDC.
    """
    secret_id = os.getenv("MAGI_SECRETS_MANAGER_SECRET_ID")
    if not secret_id:
        return

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    client: SecretsManagerClient = boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "secretsmanager", region_name=region
    )
    response = client.get_secret_value(SecretId=secret_id)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError("Secrets Manager value must be a non-empty SecretString")
    decoded: object = json.loads(secret_string)
    if not isinstance(decoded, dict):
        raise ValueError("Secrets Manager value must be a JSON object")
    payload = cast(dict[object, object], decoded)
    for name, value in payload.items():
        if not isinstance(name, str) or not name.startswith("MAGI_"):
            raise ValueError("Secrets Manager keys must use the MAGI_ prefix")
        if not isinstance(value, str):
            raise ValueError(f"Secrets Manager value for {name} must be a string")
        os.environ.setdefault(name, value)


def load_application_settings() -> tuple[Settings, EmbeddingSettings, QdrantSettings]:
    load_secrets_manager_environment()
    settings = Settings()
    embedding = EmbeddingSettings()  # pyright: ignore[reportCallIssue]
    qdrant = QdrantSettings()  # pyright: ignore[reportCallIssue]
    if embedding.vector_dimension != qdrant.vector_dimension:
        raise ValueError("embedding and Qdrant vector dimensions must match")
    return settings, embedding, qdrant


@lru_cache
def get_settings() -> Settings:
    load_secrets_manager_environment()
    return Settings()


def main() -> None:
    load_application_settings()
    print("Configuration is valid")
