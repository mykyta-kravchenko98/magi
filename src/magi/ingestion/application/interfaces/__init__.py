"""Public ingestion application ports."""

from magi.ingestion.application.interfaces.document_parser import (
    DocumentFormatParser,
    DocumentParser,
)
from magi.ingestion.application.interfaces.embedding_provider import (
    EmbeddingProvider,
)

__all__ = [
    "DocumentFormatParser",
    "DocumentParser",
    "EmbeddingProvider",
]
