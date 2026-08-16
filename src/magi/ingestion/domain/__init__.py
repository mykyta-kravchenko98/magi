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
    DeterministicDocumentRoleClassifier,
    DocumentChunker,
    DocumentNormalizer,
    DocumentRoleClassifier,
    StructureAwareCharacterChunker,
)
from magi.ingestion.domain.value_objects import (
    CharacterChunkingConfig,
    ChunkContentType,
    CodeBlock,
    ContentRole,
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
    "ContentRole",
    "DeterministicDocumentNormalizer",
    "DeterministicDocumentRoleClassifier",
    "DocumentChunk",
    "DocumentChunker",
    "DocumentNode",
    "DocumentNormalizer",
    "DocumentRoleClassifier",
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
