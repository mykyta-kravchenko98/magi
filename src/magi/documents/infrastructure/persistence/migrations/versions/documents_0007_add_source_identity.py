"""Add source fingerprint and rejection outcome to document additions.

Revision ID: documents_0007
Revises: documents_0006
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision: str = "documents_0007"
down_revision: str | None = "documents_0006"
branch_labels: str | None = None
depends_on: str | None = None

TABLE_NAME = "document_additions"
SCHEMA = "documents"

NEW_STATE_CONSTRAINT = """
    (status = 'ACCEPTED'
        AND source_object_reference IS NULL
        AND document_id IS NULL
        AND document_version_id IS NULL
        AND failure_code IS NULL
        AND failure_message IS NULL
        AND rejection_code IS NULL)
    OR
    (status = 'PROCESSING'
        AND source_object_reference IS NOT NULL
        AND document_id IS NULL
        AND document_version_id IS NULL
        AND failure_code IS NULL
        AND failure_message IS NULL
        AND rejection_code IS NULL)
    OR
    (status = 'COMPLETED'
        AND source_object_reference IS NOT NULL
        AND document_id IS NOT NULL
        AND document_version_id IS NOT NULL
        AND failure_code IS NULL
        AND failure_message IS NULL
        AND rejection_code IS NULL)
    OR
    (status = 'FAILED'
        AND document_id IS NULL
        AND document_version_id IS NULL
        AND failure_code IS NOT NULL
        AND rejection_code IS NULL)
    OR
    (status = 'REJECTED'
        AND source_fingerprint_algorithm IS NOT NULL
        AND source_fingerprint_digest IS NOT NULL
        AND source_object_reference IS NULL
        AND document_id IS NULL
        AND document_version_id IS NULL
        AND failure_code IS NULL
        AND failure_message IS NULL
        AND rejection_code IS NOT NULL)
"""

OLD_STATE_CONSTRAINT = """
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
"""


def upgrade() -> None:
    op.add_column(
        TABLE_NAME,
        sa.Column("source_fingerprint_algorithm", sa.String(length=16), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE_NAME,
        sa.Column("source_fingerprint_digest", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE_NAME,
        sa.Column(
            "rejection_code",
            sa.Enum(
                "EXACT_SOURCE_DUPLICATE",
                name="document_addition_rejection_code",
                native_enum=False,
                create_constraint=False,
                length=64,
            ),
            nullable=True,
        ),
        schema=SCHEMA,
    )
    _drop_lifecycle_constraints()
    op.create_check_constraint(
        op.f("ck_document_additions_document_addition_status"),
        TABLE_NAME,
        "status IN ('ACCEPTED', 'PROCESSING', 'COMPLETED', 'FAILED', 'REJECTED')",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        op.f("ck_document_additions_source_fingerprint_is_consistent"),
        TABLE_NAME,
        """
        (source_fingerprint_algorithm IS NULL AND source_fingerprint_digest IS NULL)
        OR
        (source_fingerprint_algorithm = 'sha256'
            AND source_fingerprint_digest ~ '^[0-9a-f]{64}$')
        """,
        schema=SCHEMA,
    )
    op.create_check_constraint(
        op.f("ck_document_additions_document_addition_rejection_code"),
        TABLE_NAME,
        "rejection_code IN ('EXACT_SOURCE_DUPLICATE')",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        op.f("ck_document_additions_state_is_consistent"),
        TABLE_NAME,
        NEW_STATE_CONSTRAINT,
        schema=SCHEMA,
    )


def downgrade() -> None:
    _drop_lifecycle_constraints()
    op.drop_constraint(
        op.f("ck_document_additions_document_addition_rejection_code"),
        TABLE_NAME,
        schema=SCHEMA,
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_document_additions_source_fingerprint_is_consistent"),
        TABLE_NAME,
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_document_additions_document_addition_status"),
        TABLE_NAME,
        "status IN ('ACCEPTED', 'PROCESSING', 'COMPLETED', 'FAILED')",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        op.f("ck_document_additions_state_is_consistent"),
        TABLE_NAME,
        OLD_STATE_CONSTRAINT,
        schema=SCHEMA,
    )
    op.drop_column(TABLE_NAME, "rejection_code", schema=SCHEMA)
    op.drop_column(TABLE_NAME, "source_fingerprint_digest", schema=SCHEMA)
    op.drop_column(TABLE_NAME, "source_fingerprint_algorithm", schema=SCHEMA)


def _drop_lifecycle_constraints() -> None:
    op.drop_constraint(
        op.f("ck_document_additions_document_addition_status"),
        TABLE_NAME,
        schema=SCHEMA,
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_document_additions_state_is_consistent"),
        TABLE_NAME,
        schema=SCHEMA,
        type_="check",
    )
