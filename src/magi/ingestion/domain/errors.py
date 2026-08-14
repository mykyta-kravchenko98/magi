"""Stable errors produced by the pure text-ingestion pipeline."""


class TextPipelineError(ValueError):
    """Base class for rejected text content or configuration."""


class UnsupportedMediaTypeError(TextPipelineError):
    """The requested parser is not part of the TXT/Markdown pipeline."""


class InvalidTextEncodingError(TextPipelineError):
    """Source bytes are not strict UTF-8 text."""


class NoTextContentError(TextPipelineError):
    """Normalization removed all meaningful text."""


class ContentBlockTooLargeError(TextPipelineError):
    """An atomic code block cannot fit the configured character limit."""


class PdfParsingError(TextPipelineError):
    """A PDF container or its embedded text layer could not be parsed."""


class PdfEncryptedError(PdfParsingError):
    """A PDF requires a password and cannot be processed."""


class PdfNoExtractableTextError(PdfParsingError):
    """A PDF has no meaningful embedded text layer."""
