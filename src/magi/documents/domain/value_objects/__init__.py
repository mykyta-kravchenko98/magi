"""Immutable values used by documents aggregates."""

from magi.documents.domain.value_objects.processing_failure import (
    ProcessingErrorCode,
    ProcessingFailure,
)
from magi.documents.domain.value_objects.rejection_outcome import (
    RejectionCode,
    RejectionOutcome,
)
from magi.documents.domain.value_objects.search_projection import SearchProjection
from magi.documents.domain.value_objects.source_file_metadata import SourceFileMetadata
from magi.documents.domain.value_objects.source_fingerprint import SourceFingerprint

__all__ = [
    "ProcessingErrorCode",
    "ProcessingFailure",
    "RejectionCode",
    "RejectionOutcome",
    "SearchProjection",
    "SourceFileMetadata",
    "SourceFingerprint",
]
