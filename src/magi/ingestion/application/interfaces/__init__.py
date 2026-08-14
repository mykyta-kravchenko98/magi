"""Public ingestion application ports."""

from magi.ingestion.application.interfaces.document_parser import (
    DocumentFormatParser,
    DocumentParser,
)

__all__ = ["DocumentFormatParser", "DocumentParser"]
