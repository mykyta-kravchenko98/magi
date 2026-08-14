"""Contract for replaceable document-chunking domain services."""

from typing import Protocol

from magi.ingestion.domain.value_objects import DocumentChunk, ParsedDocument


class DocumentChunker(Protocol):
    """Transform a normalized document into stable ordered chunks."""

    def chunk(self, document: ParsedDocument) -> tuple[DocumentChunk, ...]: ...
