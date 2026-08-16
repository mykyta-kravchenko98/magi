"""Result of creating a vector projection for a document version."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexedDocumentVersion:
    projection_reference: str
    indexed_chunk_count: int
