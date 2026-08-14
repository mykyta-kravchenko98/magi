"""SQLAlchemy model for documents."""

from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from magi.documents.domain import DocumentStatus
from magi.documents.infrastructure.persistence.base import DocumentsBase


class DocumentRow(DocumentsBase):
    __tablename__ = "documents"
    __table_args__ = (CheckConstraint("status = 'ACTIVE'", name="document_status"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    knowledge_base_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    created_from_addition_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    display_name: Mapped[str] = mapped_column(String)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            native_enum=False,
            create_constraint=False,
            length=16,
        )
    )
