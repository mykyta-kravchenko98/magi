"""Document domain model; standard-library dependencies only."""

from magi.documents.domain.document import Document, DocumentStatus
from magi.documents.domain.document_addition import DocumentAddition, DocumentAdditionStatus
from magi.documents.domain.document_version import DocumentVersion, DocumentVersionStatus
from magi.documents.domain.errors import DomainRuleViolation, InvalidStateTransition
from magi.documents.domain.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from magi.documents.domain.value_objects import (
    ProcessingErrorCode,
    ProcessingFailure,
    SearchProjection,
    SourceFileMetadata,
)

__all__ = [
    "Document",
    "DocumentAddition",
    "DocumentAdditionStatus",
    "DocumentStatus",
    "DocumentVersion",
    "DocumentVersionStatus",
    "DomainRuleViolation",
    "InvalidStateTransition",
    "KnowledgeBase",
    "KnowledgeBaseStatus",
    "ProcessingErrorCode",
    "ProcessingFailure",
    "SearchProjection",
    "SourceFileMetadata",
]
