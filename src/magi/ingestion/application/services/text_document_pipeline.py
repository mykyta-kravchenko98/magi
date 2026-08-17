"""Application service composing parse -> normalize -> chunk stages."""

from magi.ingestion.application.interfaces import DocumentParser
from magi.ingestion.application.models import IndexingContentPolicy
from magi.ingestion.domain import (
    DocumentChunk,
    DocumentChunker,
    DocumentNormalizer,
    DocumentRoleClassifier,
    DocumentStructureEnricher,
)


class TextDocumentPipeline:
    def __init__(
        self,
        *,
        parser: DocumentParser,
        normalizer: DocumentNormalizer,
        structure_enricher: DocumentStructureEnricher,
        role_classifier: DocumentRoleClassifier,
        indexing_policy: IndexingContentPolicy,
        chunker: DocumentChunker,
    ) -> None:
        self._parser = parser
        self._normalizer = normalizer
        self._structure_enricher = structure_enricher
        self._role_classifier = role_classifier
        self._indexing_policy = indexing_policy
        self._chunker = chunker

    def process(self, content: bytes, media_type: str) -> tuple[DocumentChunk, ...]:
        parsed = self._parser.parse(content, media_type)
        normalized = self._normalizer.normalize(parsed)
        enriched = self._structure_enricher.enrich(normalized)
        classified = self._role_classifier.classify(enriched)
        indexable = self._indexing_policy.select(classified)
        return self._chunker.chunk(indexable)
