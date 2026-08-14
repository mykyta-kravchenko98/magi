"""Document addition persistence interface."""

from typing import Protocol
from uuid import UUID

from magi.documents.domain import DocumentAddition


class DocumentAdditionRepository(Protocol):
    async def add(self, addition: DocumentAddition) -> None: ...

    async def get(self, addition_id: UUID) -> DocumentAddition | None: ...

    async def save(self, addition: DocumentAddition) -> None: ...
