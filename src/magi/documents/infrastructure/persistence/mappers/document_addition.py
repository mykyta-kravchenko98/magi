"""Document addition domain-to-ORM mappings."""

from magi.documents.domain import DocumentAddition, SourceFileMetadata
from magi.documents.infrastructure.persistence.mappers._value_objects import (
    failure_from_columns,
    rejection_from_column,
    source_fingerprint_from_columns,
)
from magi.documents.infrastructure.persistence.models import DocumentAdditionRow


def document_addition_to_row(addition: DocumentAddition) -> DocumentAdditionRow:
    row = DocumentAdditionRow(id=addition.id, knowledge_base_id=addition.knowledge_base_id)
    update_document_addition_row(row, addition)
    return row


def update_document_addition_row(
    row: DocumentAdditionRow,
    addition: DocumentAddition,
) -> None:
    row.original_filename = addition.source_file.original_filename
    row.media_type = addition.source_file.media_type
    row.size_bytes = addition.source_file.size_bytes
    row.source_fingerprint_algorithm = (
        addition.source_fingerprint.algorithm if addition.source_fingerprint is not None else None
    )
    row.source_fingerprint_digest = (
        addition.source_fingerprint.digest if addition.source_fingerprint is not None else None
    )
    row.status = addition.status
    row.source_object_reference = addition.source_object_reference
    row.document_id = addition.document_id
    row.document_version_id = addition.document_version_id
    row.failure_code = addition.failure.code if addition.failure is not None else None
    row.failure_message = addition.failure.message if addition.failure is not None else None
    row.rejection_code = addition.rejection.code if addition.rejection is not None else None


def document_addition_from_row(row: DocumentAdditionRow) -> DocumentAddition:
    return DocumentAddition(
        id=row.id,
        knowledge_base_id=row.knowledge_base_id,
        source_file=SourceFileMetadata(
            original_filename=row.original_filename,
            media_type=row.media_type,
            size_bytes=row.size_bytes,
        ),
        source_fingerprint=source_fingerprint_from_columns(
            row.source_fingerprint_algorithm,
            row.source_fingerprint_digest,
        ),
        status=row.status,
        source_object_reference=row.source_object_reference,
        document_id=row.document_id,
        document_version_id=row.document_version_id,
        failure=failure_from_columns(row.failure_code, row.failure_message),
        rejection=rejection_from_column(row.rejection_code),
    )
