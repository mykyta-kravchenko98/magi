"""Create the knowledge bases table.

Revision ID: documents_0002
Revises: documents_0001
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op

revision: str = "documents_0002"
down_revision: str | None = "documents_0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "ARCHIVED",
                name="knowledge_base_status",
                native_enum=False,
                create_constraint=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'ARCHIVED')",
            name=op.f("ck_knowledge_bases_knowledge_base_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_bases")),
        schema="documents",
    )


def downgrade() -> None:
    op.drop_table("knowledge_bases", schema="documents")
