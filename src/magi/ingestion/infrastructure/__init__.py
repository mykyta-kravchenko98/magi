"""Ingestion adapters."""

from magi.ingestion.infrastructure.embedding import TeiEmbeddingConfig, TeiEmbeddingProvider
from magi.ingestion.infrastructure.parsers import (
    DocumentParserRegistry,
    MarkdownParser,
    PdfExtractionProfile,
    PdfParser,
    TxtParser,
)

__all__ = [
    "DocumentParserRegistry",
    "MarkdownParser",
    "PdfExtractionProfile",
    "PdfParser",
    "TeiEmbeddingConfig",
    "TeiEmbeddingProvider",
    "TxtParser",
]
