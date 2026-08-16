"""Port for deterministic document-structure enrichment."""

from typing import Protocol

from magi.ingestion.domain.value_objects import ParsedDocument


class DocumentStructureEnricher(Protocol):
    def enrich(self, document: ParsedDocument) -> ParsedDocument: ...
