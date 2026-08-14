"""Application-owned interfaces implemented by infrastructure adapters."""

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
from magi.documents.application.interfaces.object_storage import (
    ObjectAlreadyExistsError,
    ObjectStorage,
    ObjectStorageError,
)
from magi.documents.application.interfaces.unit_of_work import UnitOfWork

__all__ = [
    "DocumentAdditionRepository",
    "DocumentRepository",
    "DocumentVersionRepository",
    "KnowledgeBaseRepository",
    "ObjectAlreadyExistsError",
    "ObjectStorage",
    "ObjectStorageError",
    "UnitOfWork",
]
