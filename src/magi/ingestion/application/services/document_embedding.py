"""Application service that prepares chunk text for document embedding."""

from collections.abc import Sequence

from magi.ingestion.application.interfaces import EmbeddingProvider
from magi.ingestion.application.models import EmbeddingBatch
from magi.ingestion.domain import DocumentChunk, compose_embedding_input


class DocumentEmbeddingService:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    async def embed(self, chunks: Sequence[DocumentChunk]) -> EmbeddingBatch:
        inputs = tuple(self._embedding_input(chunk) for chunk in chunks)
        return await self._provider.embed(inputs)

    @staticmethod
    def _embedding_input(chunk: DocumentChunk) -> str:
        return compose_embedding_input(chunk.heading_path, chunk.text)
