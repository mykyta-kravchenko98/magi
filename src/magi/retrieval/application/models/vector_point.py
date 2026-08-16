"""A point ready to be written through the vector-index port."""

from dataclasses import dataclass
from uuid import UUID

from magi.retrieval.application.models.vector_content_role import VectorContentRole
from magi.retrieval.application.models.vector_content_type import VectorContentType


@dataclass(frozen=True, slots=True, kw_only=True)
class VectorPoint:
    knowledge_base_id: UUID
    document_id: UUID
    document_version_id: UUID
    chunk_index: int
    content_type: VectorContentType
    content_role: VectorContentRole
    heading_path: tuple[str, ...]
    text: str
    vector: tuple[float, ...]
    page_start: int | None = None
    page_end: int | None = None

    def __post_init__(self) -> None:
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")
        if not self.text.strip():
            raise ValueError("vector point text must not be blank")
        if (self.page_start is None) != (self.page_end is None):
            raise ValueError("page_start and page_end must be provided together")
        if self.page_start is not None:
            if self.page_start < 1 or self.page_end is None or self.page_end < self.page_start:
                raise ValueError("page span must be positive and ordered")
