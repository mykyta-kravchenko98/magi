"""Create the retrieval database schema.

Revision ID: retrieval_0001
Revises:
Create Date: 2026-08-13
"""

from alembic import op
from sqlalchemy.schema import CreateSchema, DropSchema

from magi.retrieval.infrastructure.persistence.base import RETRIEVAL_SCHEMA

revision: str = "retrieval_0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(CreateSchema(RETRIEVAL_SCHEMA))


def downgrade() -> None:
    op.execute(DropSchema(RETRIEVAL_SCHEMA))
