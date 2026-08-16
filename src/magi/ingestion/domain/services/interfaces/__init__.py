"""Public contracts implemented by ingestion domain services."""

from magi.ingestion.domain.services.interfaces.document_chunker import DocumentChunker
from magi.ingestion.domain.services.interfaces.document_normalizer import DocumentNormalizer
from magi.ingestion.domain.services.interfaces.document_role_classifier import (
    DocumentRoleClassifier,
)

__all__ = ["DocumentChunker", "DocumentNormalizer", "DocumentRoleClassifier"]
