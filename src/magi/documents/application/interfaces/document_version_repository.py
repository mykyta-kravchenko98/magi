"""Document-version aggregate persistence interface."""

from typing import Protocol
from uuid import UUID

from magi.documents.domain import DocumentVersion


class DocumentVersionRepository(Protocol):
    async def add(self, version: DocumentVersion) -> None: ...

    async def get(self, version_id: UUID) -> DocumentVersion | None: ...

    async def save(self, version: DocumentVersion) -> None: ...
