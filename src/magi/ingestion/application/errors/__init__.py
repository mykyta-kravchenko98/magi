"""Ingestion application errors."""

from magi.ingestion.application.errors.embedding import (
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
    EmbeddingResponseInvalidError,
)

__all__ = [
    "EmbeddingProviderError",
    "EmbeddingProviderUnavailableError",
    "EmbeddingResponseInvalidError",
]
