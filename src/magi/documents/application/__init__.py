"""Public application contracts for document workflows."""

from magi.documents.application.interfaces import (
    DocumentAdditionRepository,
    DocumentRepository,
    DocumentVersionRepository,
    KnowledgeBaseRepository,
    ObjectAlreadyExistsError,
    ObjectStorage,
    ObjectStorageError,
    UnitOfWork,
)

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
