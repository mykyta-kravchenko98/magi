"""Knowledge base aggregate."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from magi.documents.domain._validation import require_text
from magi.documents.domain.errors import DomainRuleViolation, InvalidStateTransition


class KnowledgeBaseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


@dataclass(slots=True, kw_only=True)
class KnowledgeBase:
    id: UUID
    name: str
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE

    def __post_init__(self) -> None:
        require_text(self.name, "name")

    def archive(self) -> None:
        if self.status is not KnowledgeBaseStatus.ACTIVE:
            raise InvalidStateTransition("only an active knowledge base can be archived")
        self.status = KnowledgeBaseStatus.ARCHIVED

    def ensure_accepts_uploads(self) -> None:
        if self.status is not KnowledgeBaseStatus.ACTIVE:
            raise DomainRuleViolation("uploads require an active knowledge base")
