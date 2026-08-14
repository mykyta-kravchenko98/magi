"""Embedding provider adapters."""

from magi.ingestion.infrastructure.embedding.config import TeiEmbeddingConfig
from magi.ingestion.infrastructure.embedding.tei import TeiEmbeddingProvider

__all__ = ["TeiEmbeddingConfig", "TeiEmbeddingProvider"]
