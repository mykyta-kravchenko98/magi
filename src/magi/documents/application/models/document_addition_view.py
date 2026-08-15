"""Application view returned by upload and status use cases."""

from dataclasses import dataclass
from uuid import UUID

from magi.documents.domain import (
    DocumentAdditionStatus,
    DocumentVersionStatus,
    ProcessingFailure,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentAdditionView:
    document_addition_id: UUID
    status: DocumentAdditionStatus
    document_id: UUID | None
    document_version_id: UUID | None
    document_version_status: DocumentVersionStatus | None
    indexed_chunk_count: int | None
    failure: ProcessingFailure | None
