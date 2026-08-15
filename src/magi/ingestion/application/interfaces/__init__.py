"""Public ingestion application ports."""

from magi.ingestion.application.interfaces.document_content_processor import (
    DocumentContentProcessor,
)
from magi.ingestion.application.interfaces.document_embedder import DocumentEmbedder
from magi.ingestion.application.interfaces.document_parser import (
    DocumentFormatParser,
    DocumentParser,
)
from magi.ingestion.application.interfaces.embedding_provider import (
    EmbeddingProvider,
)

__all__ = [
    "DocumentContentProcessor",
    "DocumentEmbedder",
    "DocumentFormatParser",
    "DocumentParser",
    "EmbeddingProvider",
]
