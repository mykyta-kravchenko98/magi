"""Technology-neutral input for indexing one chunk."""

from dataclasses import dataclass

from magi.retrieval.application.models.vector_content_type import VectorContentType


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexChunk:
    index: int
    content_type: VectorContentType
    heading_path: tuple[str, ...]
    text: str
    vector: tuple[float, ...]
    page_start: int | None = None
    page_end: int | None = None
