"""Technology-neutral ingestion application models."""

from magi.ingestion.application.models.embedding_batch import EmbeddingBatch
from magi.ingestion.application.models.embedding_model_metadata import (
    EmbeddingModelMetadata,
)

__all__ = ["EmbeddingBatch", "EmbeddingModelMetadata"]
