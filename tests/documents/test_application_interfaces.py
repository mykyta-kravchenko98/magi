from types import TracebackType
from uuid import UUID

from magi.documents.application import (
    DocumentAdditionRepository,
    DocumentRepository,
    DocumentVersionRepository,
    KnowledgeBaseRepository,
    ObjectStorage,
    UnitOfWork,
)
from magi.documents.domain import Document, DocumentAddition, DocumentVersion, KnowledgeBase


class FakeKnowledgeBases:
    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        del knowledge_base_id
        return None


class FakeAdditions:
    async def add(self, addition: DocumentAddition) -> None:
        del addition

    async def get(self, addition_id: UUID) -> DocumentAddition | None:
        del addition_id
        return None

    async def save(self, addition: DocumentAddition) -> None:
        del addition


class FakeDocuments:
    async def add(self, document: Document) -> None:
        del document


class FakeDocumentVersions:
    async def add(self, version: DocumentVersion) -> None:
        del version

    async def get(self, version_id: UUID) -> DocumentVersion | None:
        del version_id
        return None

    async def save(self, version: DocumentVersion) -> None:
        del version


class FakeUnitOfWork:
    knowledge_bases: KnowledgeBaseRepository = FakeKnowledgeBases()
    document_additions: DocumentAdditionRepository = FakeAdditions()
    documents: DocumentRepository = FakeDocuments()
    document_versions: DocumentVersionRepository = FakeDocumentVersions()

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        del exc_type, exc_value, traceback
        return None

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class FakeObjectStorage:
    async def put(
        self,
        *,
        object_key: str,
        content: bytes,
        media_type: str,
    ) -> str:
        del content, media_type
        return object_key


def test_fakes_satisfy_structural_application_interfaces() -> None:
    unit_of_work: UnitOfWork = FakeUnitOfWork()
    object_storage: ObjectStorage = FakeObjectStorage()

    assert unit_of_work is not None
    assert object_storage is not None
