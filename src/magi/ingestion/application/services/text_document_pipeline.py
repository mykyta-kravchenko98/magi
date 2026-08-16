"""Application service composing parse -> normalize -> chunk stages."""

from magi.ingestion.application.interfaces import DocumentParser
from magi.ingestion.application.models import IndexingContentPolicy
from magi.ingestion.domain import (
    DocumentChunk,
    DocumentChunker,
    DocumentNormalizer,
    DocumentRoleClassifier,
)


class TextDocumentPipeline:
    def __init__(
        self,
        *,
        parser: DocumentParser,
        normalizer: DocumentNormalizer,
        role_classifier: DocumentRoleClassifier,
        indexing_policy: IndexingContentPolicy,
        chunker: DocumentChunker,
    ) -> None:
        self._parser = parser
        self._normalizer = normalizer
        self._role_classifier = role_classifier
        self._indexing_policy = indexing_policy
        self._chunker = chunker

    def process(self, content: bytes, media_type: str) -> tuple[DocumentChunk, ...]:
        parsed = self._parser.parse(content, media_type)
        normalized = self._normalizer.normalize(parsed)
        classified = self._role_classifier.classify(normalized)
        indexable = self._indexing_policy.select(classified)
        return self._chunker.chunk(indexable)
