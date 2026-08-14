"""Document version domain-to-ORM mappings."""

from magi.documents.domain import DocumentVersion
from magi.documents.infrastructure.persistence.mappers._value_objects import (
    failure_from_columns,
    projection_from_columns,
)
from magi.documents.infrastructure.persistence.models import DocumentVersionRow


def document_version_to_row(version: DocumentVersion) -> DocumentVersionRow:
    row = DocumentVersionRow(
        id=version.id,
        document_id=version.document_id,
        created_from_addition_id=version.created_from_addition_id,
    )
    update_document_version_row(row, version)
    return row


def update_document_version_row(row: DocumentVersionRow, version: DocumentVersion) -> None:
    row.status = version.status
    row.projection_reference = (
        version.projection.reference if version.projection is not None else None
    )
    row.indexed_chunk_count = (
        version.projection.indexed_chunk_count if version.projection is not None else None
    )
    row.failure_code = version.failure.code if version.failure is not None else None
    row.failure_message = version.failure.message if version.failure is not None else None


def document_version_from_row(row: DocumentVersionRow) -> DocumentVersion:
    return DocumentVersion(
        id=row.id,
        document_id=row.document_id,
        created_from_addition_id=row.created_from_addition_id,
        status=row.status,
        projection=projection_from_columns(
            row.projection_reference,
            row.indexed_chunk_count,
        ),
        failure=failure_from_columns(row.failure_code, row.failure_message),
    )
