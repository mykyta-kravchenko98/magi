"""SQLAlchemy model for document additions."""

from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from magi.documents.domain import DocumentAdditionStatus, ProcessingErrorCode, RejectionCode
from magi.documents.infrastructure.persistence.base import DocumentsBase


class DocumentAdditionRow(DocumentsBase):
    __tablename__ = "document_additions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACCEPTED', 'PROCESSING', 'COMPLETED', 'FAILED', 'REJECTED')",
            name="document_addition_status",
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
            "rejection_code IN ('EXACT_SOURCE_DUPLICATE')",
            name="document_addition_rejection_code",
        ),
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
        CheckConstraint(
            """
            (source_fingerprint_algorithm IS NULL AND source_fingerprint_digest IS NULL)
            OR
            (source_fingerprint_algorithm = 'sha256'
                AND source_fingerprint_digest ~ '^[0-9a-f]{64}$')
            """,
            name="source_fingerprint_is_consistent",
        ),
        CheckConstraint(
            """
            (status = 'ACCEPTED'
                AND source_object_reference IS NULL
                AND document_id IS NULL
                AND document_version_id IS NULL
                AND failure_code IS NULL
                AND failure_message IS NULL
                AND rejection_code IS NULL)
            OR
            (status = 'PROCESSING'
                AND source_object_reference IS NOT NULL
                AND document_id IS NULL
                AND document_version_id IS NULL
                AND failure_code IS NULL
                AND failure_message IS NULL
                AND rejection_code IS NULL)
            OR
            (status = 'COMPLETED'
                AND source_object_reference IS NOT NULL
                AND document_id IS NOT NULL
                AND document_version_id IS NOT NULL
                AND failure_code IS NULL
                AND failure_message IS NULL
                AND rejection_code IS NULL)
            OR
            (status = 'FAILED'
                AND document_id IS NULL
                AND document_version_id IS NULL
                AND failure_code IS NOT NULL
                AND rejection_code IS NULL)
            OR
            (status = 'REJECTED'
                AND source_fingerprint_algorithm IS NOT NULL
                AND source_fingerprint_digest IS NOT NULL
                AND source_object_reference IS NULL
                AND document_id IS NULL
                AND document_version_id IS NULL
                AND failure_code IS NULL
                AND failure_message IS NULL
                AND rejection_code IS NOT NULL)
            """,
            name="state_is_consistent",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    knowledge_base_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    original_filename: Mapped[str] = mapped_column(String)
    media_type: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    source_fingerprint_algorithm: Mapped[str | None] = mapped_column(String(16))
    source_fingerprint_digest: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[DocumentAdditionStatus] = mapped_column(
        Enum(
            DocumentAdditionStatus,
            name="document_addition_status",
            native_enum=False,
            create_constraint=False,
            length=16,
        )
    )
    source_object_reference: Mapped[str | None] = mapped_column(String)
    document_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    document_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
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
    rejection_code: Mapped[RejectionCode | None] = mapped_column(
        Enum(
            RejectionCode,
            name="document_addition_rejection_code",
            native_enum=False,
            create_constraint=False,
            length=64,
        )
    )
