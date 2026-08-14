"""Ingestion use cases, public contracts, and ports."""

from magi.ingestion.application.interfaces import (
    DocumentFormatParser,
    DocumentParser,
)
from magi.ingestion.application.text_pipeline import TextDocumentPipeline

__all__ = [
    "DocumentFormatParser",
    "DocumentParser",
    "TextDocumentPipeline",
]
