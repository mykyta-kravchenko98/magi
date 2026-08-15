"""A batch of vectors returned by an embedding provider."""

from dataclasses import dataclass

from magi.ingestion.application.models.embedding_model_metadata import (
    EmbeddingModelMetadata,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class EmbeddingBatch:
    vectors: tuple[tuple[float, ...], ...]
    model: EmbeddingModelMetadata
