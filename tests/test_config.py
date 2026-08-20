import pytest
from pydantic import ValidationError

from magi.shared import config
from magi.shared.config import EmbeddingSettings, QdrantSettings, Settings


def test_token_chunking_settings_are_read_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {
        "MAGI_CHUNK_TARGET_TOKENS": "500",
        "MAGI_CHUNK_SOFT_MAX_TOKENS": "700",
        "MAGI_CHUNK_HARD_MAX_TOKENS": "900",
        "MAGI_CHUNK_OVERLAP_TOKENS": "60",
        "MAGI_EMBEDDING_INPUT_MAX_TOKENS": "1800",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = Settings()

    assert settings.chunk_target_tokens == 500
    assert settings.chunk_soft_max_tokens == 700
    assert settings.chunk_hard_max_tokens == 900
    assert settings.chunk_overlap_tokens == 60
    assert settings.embedding_input_max_tokens == 1800


def test_adapter_settings_are_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "MAGI_EMBEDDING_BASE_URL": "https://embedding.example",
        "MAGI_EMBEDDING_MODEL_ID": "model-id",
        "MAGI_EMBEDDING_MODEL_REVISION": "model-revision",
        "MAGI_EMBEDDING_VECTOR_DIMENSION": "768",
        "MAGI_EMBEDDING_BATCH_SIZE": "8",
        "MAGI_EMBEDDING_TIMEOUT_SECONDS": "12.5",
        "MAGI_QDRANT_URL": "https://qdrant.example",
        "MAGI_QDRANT_COLLECTION": "chunks_test",
        "MAGI_QDRANT_VECTOR_DIMENSION": "768",
        "MAGI_QDRANT_BATCH_SIZE": "32",
        "MAGI_QDRANT_TIMEOUT_SECONDS": "7.5",
        "MAGI_QDRANT_API_KEY": "secret",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    embedding = EmbeddingSettings()  # pyright: ignore[reportCallIssue]
    qdrant = QdrantSettings()  # pyright: ignore[reportCallIssue]

    assert embedding.base_url == "https://embedding.example"
    assert embedding.model_id == "model-id"
    assert embedding.model_revision == "model-revision"
    assert embedding.vector_dimension == 768
    assert embedding.batch_size == 8
    assert embedding.timeout_seconds == 12.5
    assert qdrant.url == "https://qdrant.example"
    assert qdrant.collection == "chunks_test"
    assert qdrant.vector_dimension == 768
    assert qdrant.batch_size == 32
    assert qdrant.timeout_seconds == 7.5
    assert qdrant.api_key.get_secret_value() == "secret"


def test_chunk_limits_are_strictly_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAGI_CHUNK_TARGET_TOKENS", "900")
    monkeypatch.setenv("MAGI_CHUNK_SOFT_MAX_TOKENS", "800")

    with pytest.raises(ValidationError, match="chunk limits must satisfy"):
        Settings()


def test_production_requires_explicit_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAGI_ENVIRONMENT", "production")
    monkeypatch.setenv("MAGI_DOCS_ENABLED", "false")

    with pytest.raises(ValidationError, match="production requires explicit settings"):
        Settings(_env_file=None)


def test_production_disables_api_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "MAGI_ENVIRONMENT": "production",
        "MAGI_DOCS_ENABLED": "true",
        "MAGI_DATABASE_URL": "postgresql+asyncpg://user:secret@db:5432/magi",
        "MAGI_OBJECT_STORAGE_ACCESS_KEY": "access",
        "MAGI_OBJECT_STORAGE_SECRET_KEY": "secret",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError, match="MAGI_DOCS_ENABLED must be false"):
        Settings()


def test_secrets_manager_only_fills_missing_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSecretsManager:
        def get_secret_value(self, *, SecretId: str) -> dict[str, str]:
            assert SecretId == "magi/production"
            return {
                "SecretString": (
                    '{"MAGI_DATABASE_URL":"from-secret",'
                    '"MAGI_OBJECT_STORAGE_ACCESS_KEY":"secret-access"}'
                )
            }

    def fake_client(service_name: str, **kwargs: object) -> FakeSecretsManager:
        assert service_name == "secretsmanager"
        assert "region_name" in kwargs
        return FakeSecretsManager()

    config.load_secrets_manager_environment.cache_clear()
    monkeypatch.setenv("MAGI_SECRETS_MANAGER_SECRET_ID", "magi/production")
    monkeypatch.setenv("MAGI_DATABASE_URL", "explicit")
    monkeypatch.setattr(config.boto3, "client", fake_client)

    config.load_secrets_manager_environment()

    assert config.os.environ["MAGI_DATABASE_URL"] == "explicit"
    assert config.os.environ["MAGI_OBJECT_STORAGE_ACCESS_KEY"] == "secret-access"
    config.load_secrets_manager_environment.cache_clear()
