"""Values returned by an embedding provider."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class EmbeddingModelMetadata:
    model_id: str
    model_revision: str
    vector_dimension: int


@dataclass(frozen=True, slots=True, kw_only=True)
class EmbeddingBatch:
    vectors: tuple[tuple[float, ...], ...]
    model: EmbeddingModelMetadata
