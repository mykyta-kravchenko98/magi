"""Create the documents database schema.

Revision ID: documents_0001
Revises:
Create Date: 2026-08-13
"""

from alembic import op
from sqlalchemy.schema import CreateSchema, DropSchema

from magi.documents.infrastructure.persistence.base import DOCUMENTS_SCHEMA

revision: str = "documents_0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(CreateSchema(DOCUMENTS_SCHEMA))


def downgrade() -> None:
    op.execute(DropSchema(DOCUMENTS_SCHEMA))
