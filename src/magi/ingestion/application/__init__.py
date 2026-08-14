"""Ingestion use cases, public contracts, and ports."""

from magi.ingestion.application.errors import (
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
    EmbeddingResponseInvalidError,
)
from magi.ingestion.application.interfaces import (
    DocumentFormatParser,
    DocumentParser,
    EmbeddingProvider,
)
from magi.ingestion.application.text_pipeline import TextDocumentPipeline
from magi.ingestion.application.value_objects import EmbeddingBatch, EmbeddingModelMetadata

__all__ = [
    "DocumentFormatParser",
    "DocumentParser",
    "EmbeddingBatch",
    "EmbeddingModelMetadata",
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "EmbeddingProviderUnavailableError",
    "EmbeddingResponseInvalidError",
    "TextDocumentPipeline",
]
