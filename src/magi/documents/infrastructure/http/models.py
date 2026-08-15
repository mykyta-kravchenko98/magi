"""Pydantic models for the documents HTTP boundary."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel

from magi.documents.application import DocumentAdditionView
from magi.documents.domain import (
    DocumentAdditionStatus,
    DocumentVersionStatus,
    ProcessingErrorCode,
)


class ProcessingFailureResponse(BaseModel):
    code: ProcessingErrorCode
    message: str | None


class DocumentAdditionResponse(BaseModel):
    document_addition_id: UUID
    status: DocumentAdditionStatus
    document_id: UUID | None
    document_version_id: UUID | None
    document_version_status: DocumentVersionStatus | None
    indexed_chunk_count: int | None
    error: ProcessingFailureResponse | None

    @classmethod
    def from_view(cls, view: DocumentAdditionView) -> Self:
        return cls(
            document_addition_id=view.document_addition_id,
            status=view.status,
            document_id=view.document_id,
            document_version_id=view.document_version_id,
            document_version_status=view.document_version_status,
            indexed_chunk_count=view.indexed_chunk_count,
            error=(
                ProcessingFailureResponse(
                    code=view.failure.code,
                    message=view.failure.message,
                )
                if view.failure is not None
                else None
            ),
        )


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
