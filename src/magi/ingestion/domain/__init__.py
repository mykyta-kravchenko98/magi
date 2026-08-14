"""Ingestion domain services and value objects."""

from magi.ingestion.domain.errors import (
    ContentBlockTooLargeError,
    InvalidTextEncodingError,
    NoTextContentError,
    PdfEncryptedError,
    PdfNoExtractableTextError,
    PdfParsingError,
    TextPipelineError,
    UnsupportedMediaTypeError,
)
from magi.ingestion.domain.services import (
    DeterministicDocumentNormalizer,
    DocumentChunker,
    DocumentNormalizer,
    StructureAwareCharacterChunker,
)
from magi.ingestion.domain.value_objects import (
    CharacterChunkingConfig,
    ChunkContentType,
    CodeBlock,
    DocumentChunk,
    DocumentNode,
    Heading,
    Paragraph,
    ParsedDocument,
    SourceLocation,
)

__all__ = [
    "CharacterChunkingConfig",
    "ChunkContentType",
    "CodeBlock",
    "ContentBlockTooLargeError",
    "DeterministicDocumentNormalizer",
    "DocumentChunk",
    "DocumentChunker",
    "DocumentNode",
    "DocumentNormalizer",
    "Heading",
    "InvalidTextEncodingError",
    "NoTextContentError",
    "Paragraph",
    "ParsedDocument",
    "PdfEncryptedError",
    "PdfNoExtractableTextError",
    "PdfParsingError",
    "SourceLocation",
    "StructureAwareCharacterChunker",
    "TextPipelineError",
    "UnsupportedMediaTypeError",
]
