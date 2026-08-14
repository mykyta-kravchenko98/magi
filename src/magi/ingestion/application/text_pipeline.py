"""Public composition of the parse -> normalize -> chunk stages."""

from magi.ingestion.application.interfaces import DocumentParser
from magi.ingestion.domain import (
    DocumentChunk,
    DocumentChunker,
    DocumentNormalizer,
)


class TextDocumentPipeline:
    def __init__(
        self,
        *,
        parser: DocumentParser,
        normalizer: DocumentNormalizer,
        chunker: DocumentChunker,
    ) -> None:
        self._parser = parser
        self._normalizer = normalizer
        self._chunker = chunker

    def process(self, content: bytes, media_type: str) -> tuple[DocumentChunk, ...]:
        parsed = self._parser.parse(content, media_type)
        normalized = self._normalizer.normalize(parsed)
        return self._chunker.chunk(normalized)
