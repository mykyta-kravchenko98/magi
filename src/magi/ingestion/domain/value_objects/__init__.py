"""Public ingestion domain value objects."""

from magi.ingestion.domain.value_objects.chunking_profile import TokenChunkingProfile
from magi.ingestion.domain.value_objects.content_role import ContentRole
from magi.ingestion.domain.value_objects.document_chunk import (
    ChunkContentType,
    DocumentChunk,
    compose_embedding_input,
)
from magi.ingestion.domain.value_objects.document_structure import (
    CodeBlock,
    DocumentNode,
    Heading,
    Paragraph,
    ParsedDocument,
)
from magi.ingestion.domain.value_objects.source_location import SourceLocation

__all__ = [
    "ChunkContentType",
    "CodeBlock",
    "ContentRole",
    "DocumentChunk",
    "DocumentNode",
    "Heading",
    "Paragraph",
    "ParsedDocument",
    "SourceLocation",
    "TokenChunkingProfile",
    "compose_embedding_input",
]
