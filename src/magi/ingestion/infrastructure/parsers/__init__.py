"""Concrete document-format parser adapters and their media-type registry."""

from magi.ingestion.infrastructure.parsers.markdown import MarkdownParser
from magi.ingestion.infrastructure.parsers.pdf import PdfExtractionProfile, PdfParser
from magi.ingestion.infrastructure.parsers.registry import DocumentParserRegistry
from magi.ingestion.infrastructure.parsers.txt import TxtParser

__all__ = [
    "DocumentParserRegistry",
    "MarkdownParser",
    "PdfExtractionProfile",
    "PdfParser",
    "TxtParser",
]
