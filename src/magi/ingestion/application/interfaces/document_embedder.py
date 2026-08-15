"""Heading-aware document embedding application contract."""

from collections.abc import Sequence
from typing import Protocol

from magi.ingestion.application.models import EmbeddingBatch
from magi.ingestion.domain import DocumentChunk


class DocumentEmbedder(Protocol):
    async def embed(self, chunks: Sequence[DocumentChunk]) -> EmbeddingBatch: ...
