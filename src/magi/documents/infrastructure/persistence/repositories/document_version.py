"""PostgreSQL document-version repository."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from magi.documents.domain import DocumentVersion
from magi.documents.infrastructure.persistence.mappers.document_version import (
    document_version_from_row,
    document_version_to_row,
    update_document_version_row,
)
from magi.documents.infrastructure.persistence.models import DocumentVersionRow
from magi.documents.infrastructure.persistence.repositories.errors import (
    AggregateNotFoundError,
)


class SqlAlchemyDocumentVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, version: DocumentVersion) -> None:
        self._session.add(document_version_to_row(version))

    async def get(self, version_id: UUID) -> DocumentVersion | None:
        row = await self._session.get(DocumentVersionRow, version_id)
        return document_version_from_row(row) if row is not None else None

    async def save(self, version: DocumentVersion) -> None:
        row = await self._session.get(DocumentVersionRow, version.id)
        if row is None:
            raise AggregateNotFoundError(f"document version {version.id} does not exist")
        update_document_version_row(row, version)
