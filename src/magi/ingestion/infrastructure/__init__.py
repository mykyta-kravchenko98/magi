"""Ingestion adapters."""

from magi.ingestion.infrastructure.embedding import TeiEmbeddingConfig, TeiEmbeddingProvider
from magi.ingestion.infrastructure.parsers import (
    DocumentParserRegistry,
    MarkdownParser,
    PdfExtractionProfile,
    PdfParser,
    TxtParser,
)
from magi.ingestion.infrastructure.tokenization import (
    HuggingFaceTokenCounter,
    HuggingFaceTokenizerConfig,
)

__all__ = [
    "DocumentParserRegistry",
    "HuggingFaceTokenCounter",
    "HuggingFaceTokenizerConfig",
    "MarkdownParser",
    "PdfExtractionProfile",
    "PdfParser",
    "TeiEmbeddingConfig",
    "TeiEmbeddingProvider",
    "TxtParser",
]
