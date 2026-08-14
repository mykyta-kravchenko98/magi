"""Document aggregate."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from magi.documents.domain._validation import require_text


class DocumentStatus(StrEnum):
    ACTIVE = "ACTIVE"


@dataclass(frozen=True, slots=True, kw_only=True)
class Document:
    id: UUID
    knowledge_base_id: UUID
    created_from_addition_id: UUID
    display_name: str
    status: DocumentStatus = DocumentStatus.ACTIVE

    def __post_init__(self) -> None:
        require_text(self.display_name, "display_name")
