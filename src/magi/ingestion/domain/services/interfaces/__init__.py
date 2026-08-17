"""Public contracts implemented by ingestion domain services."""

from magi.ingestion.domain.services.interfaces.document_chunker import DocumentChunker
from magi.ingestion.domain.services.interfaces.document_normalizer import DocumentNormalizer
from magi.ingestion.domain.services.interfaces.document_role_classifier import (
    DocumentRoleClassifier,
)
from magi.ingestion.domain.services.interfaces.document_structure_enricher import (
    DocumentStructureEnricher,
)
from magi.ingestion.domain.services.interfaces.token_counter import TokenCounter

__all__ = [
    "DocumentChunker",
    "DocumentNormalizer",
    "DocumentRoleClassifier",
    "DocumentStructureEnricher",
    "TokenCounter",
]
