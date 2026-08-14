"""SQLAlchemy model for document versions."""

from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from magi.documents.domain import DocumentVersionStatus, ProcessingErrorCode
from magi.documents.infrastructure.persistence.base import DocumentsBase


class DocumentVersionRow(DocumentsBase):
    __tablename__ = "document_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROCESSING', 'SEARCHABLE', 'FAILED')",
            name="document_version_status",
        ),
        CheckConstraint(
            """
            failure_code IN (
                'OBJECT_STORAGE_UNAVAILABLE',
                'PARSING_FAILED',
                'PDF_ENCRYPTED',
                'NO_EXTRACTABLE_TEXT',
                'CONTENT_BLOCK_TOO_LARGE',
                'EMBEDDING_PROVIDER_UNAVAILABLE',
                'EMBEDDING_RESPONSE_INVALID',
                'VECTOR_INDEX_UNAVAILABLE',
                'PROCESSING_FAILED'
            )
            """,
            name="processing_error_code",
        ),
        CheckConstraint(
            """
            (status = 'PROCESSING'
                AND projection_reference IS NULL
                AND indexed_chunk_count IS NULL
                AND failure_code IS NULL
                AND failure_message IS NULL)
            OR
            (status = 'SEARCHABLE'
                AND projection_reference IS NOT NULL
                AND indexed_chunk_count > 0
                AND failure_code IS NULL
                AND failure_message IS NULL)
            OR
            (status = 'FAILED'
                AND projection_reference IS NULL
                AND indexed_chunk_count IS NULL
                AND failure_code IS NOT NULL)
            """,
            name="state_is_consistent",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    created_from_addition_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    status: Mapped[DocumentVersionStatus] = mapped_column(
        Enum(
            DocumentVersionStatus,
            name="document_version_status",
            native_enum=False,
            create_constraint=False,
            length=16,
        )
    )
    projection_reference: Mapped[str | None] = mapped_column(String)
    indexed_chunk_count: Mapped[int | None] = mapped_column(Integer)
    failure_code: Mapped[ProcessingErrorCode | None] = mapped_column(
        Enum(
            ProcessingErrorCode,
            name="processing_error_code",
            native_enum=False,
            create_constraint=False,
            length=64,
        )
    )
    failure_message: Mapped[str | None] = mapped_column(String)
