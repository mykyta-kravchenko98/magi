"""Create the documents table.

Revision ID: documents_0004
Revises: documents_0003
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op

revision: str = "documents_0004"
down_revision: str | None = "documents_0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), nullable=False),
        sa.Column("created_from_addition_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                name="document_status",
                native_enum=False,
                create_constraint=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status = 'ACTIVE'",
            name=op.f("ck_documents_document_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        schema="documents",
    )
    op.create_index(
        op.f("ix_documents_documents_created_from_addition_id"),
        "documents",
        ["created_from_addition_id"],
        unique=False,
        schema="documents",
    )
    op.create_index(
        op.f("ix_documents_documents_knowledge_base_id"),
        "documents",
        ["knowledge_base_id"],
        unique=False,
        schema="documents",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_documents_documents_knowledge_base_id"),
        table_name="documents",
        schema="documents",
    )
    op.drop_index(
        op.f("ix_documents_documents_created_from_addition_id"),
        table_name="documents",
        schema="documents",
    )
    op.drop_table("documents", schema="documents")
