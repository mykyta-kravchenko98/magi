"""PostgreSQL document repository."""

from sqlalchemy.ext.asyncio import AsyncSession

from magi.documents.domain import Document
from magi.documents.infrastructure.persistence.mappers.document import document_to_row


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: Document) -> None:
        self._session.add(document_to_row(document))
