"""Seed the technical literature knowledge base.

Revision ID: documents_0006
Revises: documents_0005
Create Date: 2026-08-14
"""

from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "documents_0006"
down_revision: str | None = "documents_0005"
branch_labels: str | None = None
depends_on: str | None = None

TECHNICAL_LITERATURE_KNOWLEDGE_BASE_ID = UUID("c87d83a0-eac5-4a2c-9b7d-31fbdce39f51")
TECHNICAL_LITERATURE_KNOWLEDGE_BASE_NAME = "Technical Literature"

knowledge_bases = sa.table(
    "knowledge_bases",
    sa.column("id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("status", sa.String()),
    schema="documents",
)


def upgrade() -> None:
    op.bulk_insert(
        knowledge_bases,
        [
            {
                "id": TECHNICAL_LITERATURE_KNOWLEDGE_BASE_ID,
                "name": TECHNICAL_LITERATURE_KNOWLEDGE_BASE_NAME,
                "status": "ACTIVE",
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        knowledge_bases.delete().where(
            knowledge_bases.c.id == TECHNICAL_LITERATURE_KNOWLEDGE_BASE_ID
        )
    )
