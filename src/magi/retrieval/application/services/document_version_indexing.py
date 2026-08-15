"""Application service for creating a document-version vector projection."""

from collections.abc import Sequence
from uuid import UUID

from magi.retrieval.application.interfaces.vector_index import VectorIndex
from magi.retrieval.application.models import (
    IndexChunk,
    IndexedDocumentVersion,
    VectorPoint,
)


class DocumentVersionIndexingService:
    def __init__(self, vector_index: VectorIndex) -> None:
        self._vector_index = vector_index

    async def index(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
        document_version_id: UUID,
        chunks: Sequence[IndexChunk],
    ) -> IndexedDocumentVersion:
        collection = await self._vector_index.ensure_collection()
        points = tuple(
            VectorPoint(
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                document_version_id=document_version_id,
                chunk_index=chunk.index,
                content_type=chunk.content_type,
                heading_path=chunk.heading_path,
                text=chunk.text,
                vector=chunk.vector,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
            for chunk in chunks
        )
        indexed_count = await self._vector_index.upsert(points)
        return IndexedDocumentVersion(
            projection_reference=collection,
            indexed_chunk_count=indexed_count,
        )
