"""Document aggregate persistence interface."""

from typing import Protocol

from magi.documents.domain import Document


class DocumentRepository(Protocol):
    async def add(self, document: Document) -> None: ...
