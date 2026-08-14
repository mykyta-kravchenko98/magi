"""Search projection value object."""

from dataclasses import dataclass

from magi.documents.domain._validation import require_text
from magi.documents.domain.errors import DomainRuleViolation


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchProjection:
    reference: str
    indexed_chunk_count: int

    def __post_init__(self) -> None:
        require_text(self.reference, "reference")
        if self.indexed_chunk_count <= 0:
            raise DomainRuleViolation("indexed_chunk_count must be positive")
