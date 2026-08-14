"""Create the document additions table.

Revision ID: documents_0003
Revises: documents_0002
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op

revision: str = "documents_0003"
down_revision: str | None = "documents_0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "document_additions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACCEPTED",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                name="document_addition_status",
                native_enum=False,
                create_constraint=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("source_object_reference", sa.String(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("document_version_id", sa.Uuid(), nullable=True),
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
            "status IN ('ACCEPTED', 'PROCESSING', 'COMPLETED', 'FAILED')",
            name=op.f("ck_document_additions_document_addition_status"),
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
            name=op.f("ck_document_additions_processing_error_code"),
        ),
        sa.CheckConstraint(
            """
            (status = 'ACCEPTED'
                AND source_object_reference IS NULL
                AND document_id IS NULL
                AND document_version_id IS NULL
                AND failure_code IS NULL
                AND failure_message IS NULL)
            OR
            (status = 'PROCESSING'
                AND source_object_reference IS NOT NULL
                AND document_id IS NULL
                AND document_version_id IS NULL
                AND failure_code IS NULL
                AND failure_message IS NULL)
            OR
            (status = 'COMPLETED'
                AND source_object_reference IS NOT NULL
                AND document_id IS NOT NULL
                AND document_version_id IS NOT NULL
                AND failure_code IS NULL
                AND failure_message IS NULL)
            OR
            (status = 'FAILED'
                AND document_id IS NULL
                AND document_version_id IS NULL
                AND failure_code IS NOT NULL)
            """,
            name=op.f("ck_document_additions_state_is_consistent"),
        ),
        sa.CheckConstraint(
            "size_bytes > 0",
            name=op.f("ck_document_additions_size_bytes_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_additions")),
        schema="documents",
    )
    op.create_index(
        op.f("ix_documents_document_additions_knowledge_base_id"),
        "document_additions",
        ["knowledge_base_id"],
        unique=False,
        schema="documents",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_documents_document_additions_knowledge_base_id"),
        table_name="document_additions",
        schema="documents",
    )
    op.drop_table("document_additions", schema="documents")
