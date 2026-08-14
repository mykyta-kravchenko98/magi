"""Public application contracts for document workflows."""

from magi.documents.application.ports import (
    DocumentAdditionRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
    ObjectStorage,
    UnitOfWork,
)

__all__ = [
    "DocumentAdditionRepository",
    "DocumentRepository",
    "KnowledgeBaseRepository",
    "ObjectStorage",
    "UnitOfWork",
]
