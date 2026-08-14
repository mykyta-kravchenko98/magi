"""Contract for replaceable document-normalization domain services."""

from typing import Protocol

from magi.ingestion.domain.value_objects import ParsedDocument


class DocumentNormalizer(Protocol):
    """Normalize parsed structure while retaining its provenance."""

    def normalize(self, document: ParsedDocument) -> ParsedDocument: ...
