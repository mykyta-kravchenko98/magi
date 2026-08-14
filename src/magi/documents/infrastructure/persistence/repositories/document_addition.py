"""PostgreSQL document addition repository."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from magi.documents.domain import DocumentAddition
from magi.documents.infrastructure.persistence.mappers.document_addition import (
    document_addition_from_row,
    document_addition_to_row,
    update_document_addition_row,
)
from magi.documents.infrastructure.persistence.models import DocumentAdditionRow
from magi.documents.infrastructure.persistence.repositories.errors import (
    AggregateNotFoundError,
)


class SqlAlchemyDocumentAdditionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, addition: DocumentAddition) -> None:
        self._session.add(document_addition_to_row(addition))

    async def get(self, addition_id: UUID) -> DocumentAddition | None:
        row = await self._session.get(DocumentAdditionRow, addition_id)
        return document_addition_from_row(row) if row is not None else None

    async def save(self, addition: DocumentAddition) -> None:
        row = await self._session.get(DocumentAdditionRow, addition.id)
        if row is None:
            raise AggregateNotFoundError(f"document addition {addition.id} does not exist")
        update_document_addition_row(row, addition)
