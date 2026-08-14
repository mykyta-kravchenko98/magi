"""SQLAlchemy models owned by the documents context."""

from magi.documents.infrastructure.persistence.base import DocumentsBase
from magi.documents.infrastructure.persistence.models.document import DocumentRow
from magi.documents.infrastructure.persistence.models.document_addition import (
    DocumentAdditionRow,
)
from magi.documents.infrastructure.persistence.models.document_version import DocumentVersionRow
from magi.documents.infrastructure.persistence.models.knowledge_base import KnowledgeBaseRow

MODEL_METADATA = DocumentsBase.metadata

__all__ = [
    "MODEL_METADATA",
    "DocumentAdditionRow",
    "DocumentRow",
    "DocumentVersionRow",
    "KnowledgeBaseRow",
]
