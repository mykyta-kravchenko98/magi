"""Infrastructure-facing ports owned by the documents application layer."""

from types import TracebackType
from typing import Protocol
from uuid import UUID

from magi.documents.domain import Document, DocumentAddition, DocumentVersion, KnowledgeBase


class KnowledgeBaseRepository(Protocol):
    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None: ...


class DocumentAdditionRepository(Protocol):
    async def add(self, addition: DocumentAddition) -> None: ...

    async def get(self, addition_id: UUID) -> DocumentAddition | None: ...


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None: ...

    async def add_version(self, version: DocumentVersion) -> None: ...

    async def get_version(self, version_id: UUID) -> DocumentVersion | None: ...


class UnitOfWork(Protocol):
    knowledge_bases: KnowledgeBaseRepository
    document_additions: DocumentAdditionRepository
    documents: DocumentRepository

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class ObjectStorage(Protocol):
    """Stores immutable source bytes and returns an opaque reference."""

    async def put(
        self,
        *,
        object_key: str,
        content: bytes,
        media_type: str,
    ) -> str: ...
