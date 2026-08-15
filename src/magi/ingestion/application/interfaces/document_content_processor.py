"""Document content processing application contract."""

from typing import Protocol

from magi.ingestion.domain import DocumentChunk


class DocumentContentProcessor(Protocol):
    def process(self, content: bytes, media_type: str) -> tuple[DocumentChunk, ...]: ...
