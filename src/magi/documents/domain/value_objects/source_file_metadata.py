"""Source file metadata value object."""

from dataclasses import dataclass

from magi.documents.domain._validation import require_text
from magi.documents.domain.errors import DomainRuleViolation


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceFileMetadata:
    original_filename: str
    media_type: str
    size_bytes: int

    def __post_init__(self) -> None:
        require_text(self.original_filename, "original_filename")
        require_text(self.media_type, "media_type")
        if self.size_bytes <= 0:
            raise DomainRuleViolation("size_bytes must be positive")
