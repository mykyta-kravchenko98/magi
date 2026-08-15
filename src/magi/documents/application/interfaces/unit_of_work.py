"""Transaction boundary for documents persistence."""

from types import TracebackType
from typing import Protocol

from magi.documents.application.interfaces.document_addition_repository import (
    DocumentAdditionRepository,
)
from magi.documents.application.interfaces.document_repository import DocumentRepository
from magi.documents.application.interfaces.document_version_repository import (
    DocumentVersionRepository,
)
from magi.documents.application.interfaces.knowledge_base_repository import (
    KnowledgeBaseRepository,
)


class UnitOfWork(Protocol):
    @property
    def knowledge_bases(self) -> KnowledgeBaseRepository: ...

    @property
    def document_additions(self) -> DocumentAdditionRepository: ...

    @property
    def documents(self) -> DocumentRepository: ...

    @property
    def document_versions(self) -> DocumentVersionRepository: ...

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
