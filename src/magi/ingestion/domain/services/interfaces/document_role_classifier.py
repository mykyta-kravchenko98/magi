"""Port for assigning semantic roles to normalized document nodes."""

from typing import Protocol

from magi.ingestion.domain.value_objects import ParsedDocument


class DocumentRoleClassifier(Protocol):
    def classify(self, document: ParsedDocument) -> ParsedDocument: ...
