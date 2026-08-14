"""Create the ingestion database schema.

Revision ID: ingestion_0001
Revises:
Create Date: 2026-08-13
"""

from alembic import op
from sqlalchemy.schema import CreateSchema, DropSchema

from magi.ingestion.infrastructure.persistence.base import INGESTION_SCHEMA

revision: str = "ingestion_0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(CreateSchema(INGESTION_SCHEMA))


def downgrade() -> None:
    op.execute(DropSchema(INGESTION_SCHEMA))
