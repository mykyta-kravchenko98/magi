"""Knowledge base persistence interface."""

from typing import Protocol
from uuid import UUID

from magi.documents.domain import KnowledgeBase


class KnowledgeBaseRepository(Protocol):
    async def get(self, knowledge_base_id: UUID) -> KnowledgeBase | None: ...
