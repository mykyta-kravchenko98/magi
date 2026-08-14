"""Immutable values used by documents aggregates."""

from magi.documents.domain.value_objects.processing_failure import (
    ProcessingErrorCode,
    ProcessingFailure,
)
from magi.documents.domain.value_objects.search_projection import SearchProjection
from magi.documents.domain.value_objects.source_file_metadata import SourceFileMetadata

__all__ = [
    "ProcessingErrorCode",
    "ProcessingFailure",
    "SearchProjection",
    "SourceFileMetadata",
]
