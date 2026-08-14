"""Retrieval application errors."""

from magi.retrieval.application.errors.vector_index import (
    VectorIndexConfigurationError,
    VectorIndexError,
    VectorIndexUnavailableError,
    VectorPointInvalidError,
)

__all__ = [
    "VectorIndexConfigurationError",
    "VectorIndexError",
    "VectorIndexUnavailableError",
    "VectorPointInvalidError",
]
