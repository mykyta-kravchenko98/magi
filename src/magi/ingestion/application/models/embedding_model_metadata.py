"""Metadata identifying vectors produced by an embedding model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class EmbeddingModelMetadata:
    model_id: str
    model_revision: str
    vector_dimension: int
