"""Document-version indexing application contract."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from magi.retrieval.application.models import IndexChunk, IndexedDocumentVersion


class DocumentVersionIndexer(Protocol):
    async def index(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
        document_version_id: UUID,
        chunks: Sequence[IndexChunk],
    ) -> IndexedDocumentVersion: ...
