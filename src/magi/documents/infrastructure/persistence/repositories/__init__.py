"""PostgreSQL repository adapters owned by the documents context."""

from magi.documents.infrastructure.persistence.repositories.document import (
    SqlAlchemyDocumentRepository,
)
from magi.documents.infrastructure.persistence.repositories.document_addition import (
    SqlAlchemyDocumentAdditionRepository,
)
from magi.documents.infrastructure.persistence.repositories.document_version import (
    SqlAlchemyDocumentVersionRepository,
)
from magi.documents.infrastructure.persistence.repositories.errors import AggregateNotFoundError
from magi.documents.infrastructure.persistence.repositories.knowledge_base import (
    SqlAlchemyKnowledgeBaseRepository,
)

__all__ = [
    "AggregateNotFoundError",
    "SqlAlchemyDocumentAdditionRepository",
    "SqlAlchemyDocumentRepository",
    "SqlAlchemyDocumentVersionRepository",
    "SqlAlchemyKnowledgeBaseRepository",
]
