"""Public ingestion domain value objects."""

from magi.ingestion.domain.value_objects.chunking_profile import CharacterChunkingConfig
from magi.ingestion.domain.value_objects.document_chunk import ChunkContentType, DocumentChunk
from magi.ingestion.domain.value_objects.document_structure import (
    CodeBlock,
    DocumentNode,
    Heading,
    Paragraph,
    ParsedDocument,
)
from magi.ingestion.domain.value_objects.source_location import SourceLocation

__all__ = [
    "CharacterChunkingConfig",
    "ChunkContentType",
    "CodeBlock",
    "DocumentChunk",
    "DocumentNode",
    "Heading",
    "Paragraph",
    "ParsedDocument",
    "SourceLocation",
]
