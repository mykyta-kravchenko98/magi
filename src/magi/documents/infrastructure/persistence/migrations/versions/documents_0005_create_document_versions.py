"""Create the document versions table.

Revision ID: documents_0005
Revises: documents_0004
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op

revision: str = "documents_0005"
down_revision: str | None = "documents_0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("created_from_addition_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PROCESSING",
                "SEARCHABLE",
                "FAILED",
                name="document_version_status",
                native_enum=False,
                create_constraint=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("projection_reference", sa.String(), nullable=True),
        sa.Column("indexed_chunk_count", sa.Integer(), nullable=True),
        sa.Column(
            "failure_code",
            sa.Enum(
                "OBJECT_STORAGE_UNAVAILABLE",
                "PARSING_FAILED",
                "PDF_ENCRYPTED",
                "NO_EXTRACTABLE_TEXT",
                "CONTENT_BLOCK_TOO_LARGE",
                "EMBEDDING_PROVIDER_UNAVAILABLE",
                "EMBEDDING_RESPONSE_INVALID",
                "VECTOR_INDEX_UNAVAILABLE",
                "PROCESSING_FAILED",
                name="processing_error_code",
                native_enum=False,
                create_constraint=False,
                length=64,
            ),
            nullable=True,
        ),
        sa.Column("failure_message", sa.String(), nullable=True),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'SEARCHABLE', 'FAILED')",
            name=op.f("ck_document_versions_document_version_status"),
        ),
        sa.CheckConstraint(
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
            name=op.f("ck_document_versions_processing_error_code"),
        ),
        sa.CheckConstraint(
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
            name=op.f("ck_document_versions_state_is_consistent"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_versions")),
        schema="documents",
    )
    op.create_index(
        op.f("ix_documents_document_versions_created_from_addition_id"),
        "document_versions",
        ["created_from_addition_id"],
        unique=False,
        schema="documents",
    )
    op.create_index(
        op.f("ix_documents_document_versions_document_id"),
        "document_versions",
        ["document_id"],
        unique=False,
        schema="documents",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_documents_document_versions_document_id"),
        table_name="document_versions",
        schema="documents",
    )
    op.drop_index(
        op.f("ix_documents_document_versions_created_from_addition_id"),
        table_name="document_versions",
        schema="documents",
    )
    op.drop_table("document_versions", schema="documents")
