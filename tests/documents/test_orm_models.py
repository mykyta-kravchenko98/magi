from sqlalchemy import CheckConstraint, Enum

from magi.documents.infrastructure.persistence.base import DOCUMENTS_SCHEMA, DocumentsBase
from magi.documents.infrastructure.persistence.models import (
    DocumentAdditionRow,
    DocumentRow,
    DocumentVersionRow,
    KnowledgeBaseRow,
)


def test_documents_context_owns_four_product_tables() -> None:
    assert set(DocumentsBase.metadata.tables) == {
        "documents.knowledge_bases",
        "documents.document_additions",
        "documents.documents",
        "documents.document_versions",
    }
    assert all(table.schema == DOCUMENTS_SCHEMA for table in DocumentsBase.metadata.tables.values())


def test_value_objects_are_flattened_into_aggregate_tables() -> None:
    assert set(DocumentAdditionRow.__table__.columns.keys()) >= {
        "original_filename",
        "media_type",
        "size_bytes",
        "source_fingerprint_algorithm",
        "source_fingerprint_digest",
        "failure_code",
        "failure_message",
        "rejection_code",
    }
    assert set(DocumentVersionRow.__table__.columns.keys()) >= {
        "projection_reference",
        "indexed_chunk_count",
        "failure_code",
        "failure_message",
    }


def test_lifecycle_enums_are_non_native_and_schema_local() -> None:
    status_columns = (
        KnowledgeBaseRow.status,
        DocumentAdditionRow.status,
        DocumentRow.status,
        DocumentVersionRow.status,
    )

    for status_column in status_columns:
        column_type = status_column.property.columns[0].type
        assert isinstance(column_type, Enum)
        assert column_type.native_enum is False


def test_stateful_tables_have_database_invariant_constraints() -> None:
    addition_table = DocumentsBase.metadata.tables["documents.document_additions"]
    version_table = DocumentsBase.metadata.tables["documents.document_versions"]
    addition_checks = {
        constraint.name
        for constraint in addition_table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    version_checks = {
        constraint.name
        for constraint in version_table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_document_additions_size_bytes_positive" in addition_checks
    assert "ck_document_additions_state_is_consistent" in addition_checks
    assert "ck_document_additions_source_fingerprint_is_consistent" in addition_checks
    assert "ck_document_additions_document_addition_rejection_code" in addition_checks
    assert "ck_document_versions_state_is_consistent" in version_checks


def test_aggregate_references_are_scalar_ids_without_orm_relationships() -> None:
    rows = (KnowledgeBaseRow, DocumentAdditionRow, DocumentRow, DocumentVersionRow)

    assert all(not row.__mapper__.relationships for row in rows)
    assert all(not table.foreign_keys for table in DocumentsBase.metadata.tables.values())
