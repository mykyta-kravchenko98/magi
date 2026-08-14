"""PostgreSQL knowledge base repository."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from magi.documents.domain import KnowledgeBase
from magi.documents.infrastructure.persistence.mappers.knowledge_base import (
    knowledge_base_from_row,
)
from magi.documents.infrastructure.persistence.models import KnowledgeBaseRow


class SqlAlchemyKnowledgeBaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        row = await self._session.get(KnowledgeBaseRow, knowledge_base_id)
        return knowledge_base_from_row(row) if row is not None else None
