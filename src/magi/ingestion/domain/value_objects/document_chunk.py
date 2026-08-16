"""Immutable chunk values produced for downstream embedding and indexing."""

from dataclasses import dataclass
from enum import StrEnum

from magi.ingestion.domain.value_objects.content_role import ContentRole


class ChunkContentType(StrEnum):
    TEXT = "text"
    CODE = "code"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentChunk:
    index: int
    text: str
    heading_path: tuple[str, ...]
    content_type: ChunkContentType
    content_role: ContentRole = ContentRole.BODY
    source_line_start: int | None = None
    source_line_end: int | None = None
    page_start: int | None = None
    page_end: int | None = None
