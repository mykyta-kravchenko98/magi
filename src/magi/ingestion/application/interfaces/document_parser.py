"""Application-owned parser ports."""

from typing import Protocol

from magi.ingestion.domain import ParsedDocument


class DocumentFormatParser(Protocol):
    """Parse bytes of one concrete document format."""

    def parse(self, content: bytes) -> ParsedDocument: ...


class DocumentParser(Protocol):
    """Resolve a supported media type and parse its source bytes."""

    def parse(self, content: bytes, media_type: str) -> ParsedDocument: ...
