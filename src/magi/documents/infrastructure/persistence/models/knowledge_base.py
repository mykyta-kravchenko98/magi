"""SQLAlchemy model for knowledge bases."""

from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from magi.documents.domain import KnowledgeBaseStatus
from magi.documents.infrastructure.persistence.base import DocumentsBase


class KnowledgeBaseRow(DocumentsBase):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'ARCHIVED')",
            name="knowledge_base_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    status: Mapped[KnowledgeBaseStatus] = mapped_column(
        Enum(
            KnowledgeBaseStatus,
            name="knowledge_base_status",
            native_enum=False,
            create_constraint=False,
            length=16,
        )
    )
