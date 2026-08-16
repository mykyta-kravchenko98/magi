"""Ingestion use cases, public contracts, and ports."""

from magi.ingestion.application.errors import (
    EmbeddingProviderError,
    EmbeddingProviderUnavailableError,
    EmbeddingResponseInvalidError,
)
from magi.ingestion.application.interfaces import (
    DocumentContentProcessor,
    DocumentEmbedder,
    DocumentFormatParser,
    DocumentParser,
    EmbeddingProvider,
)
from magi.ingestion.application.models import (
    EmbeddingBatch,
    EmbeddingModelMetadata,
    IndexingContentPolicy,
)
from magi.ingestion.application.services import (
    DocumentEmbeddingService,
    TextDocumentPipeline,
)

__all__ = [
    "DocumentContentProcessor",
    "DocumentEmbedder",
    "DocumentEmbeddingService",
    "DocumentFormatParser",
    "DocumentParser",
    "EmbeddingBatch",
    "EmbeddingModelMetadata",
    "EmbeddingProvider",
    "EmbeddingProviderError",
    "EmbeddingProviderUnavailableError",
    "EmbeddingResponseInvalidError",
    "IndexingContentPolicy",
    "TextDocumentPipeline",
]
