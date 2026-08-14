"""Persisted processing failure value object."""

from dataclasses import dataclass
from enum import StrEnum

from magi.documents.domain._validation import require_text


class ProcessingErrorCode(StrEnum):
    OBJECT_STORAGE_UNAVAILABLE = "OBJECT_STORAGE_UNAVAILABLE"
    PARSING_FAILED = "PARSING_FAILED"
    PDF_ENCRYPTED = "PDF_ENCRYPTED"
    NO_EXTRACTABLE_TEXT = "NO_EXTRACTABLE_TEXT"
    CONTENT_BLOCK_TOO_LARGE = "CONTENT_BLOCK_TOO_LARGE"
    EMBEDDING_PROVIDER_UNAVAILABLE = "EMBEDDING_PROVIDER_UNAVAILABLE"
    EMBEDDING_RESPONSE_INVALID = "EMBEDDING_RESPONSE_INVALID"
    VECTOR_INDEX_UNAVAILABLE = "VECTOR_INDEX_UNAVAILABLE"
    PROCESSING_FAILED = "PROCESSING_FAILED"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingFailure:
    code: ProcessingErrorCode
    message: str | None = None

    def __post_init__(self) -> None:
        if self.message is not None:
            require_text(self.message, "message")
