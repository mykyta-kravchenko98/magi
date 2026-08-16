"""Map pipeline exceptions to stable persisted failure codes."""

from magi.documents.application.errors import ObjectStorageError
from magi.documents.domain import ProcessingErrorCode, ProcessingFailure
from magi.ingestion.application import (
    EmbeddingProviderUnavailableError,
    EmbeddingResponseInvalidError,
)
from magi.ingestion.domain import (
    ContentBlockTooLargeError,
    InvalidTextEncodingError,
    NoTextContentError,
    PdfEncryptedError,
    PdfNoExtractableTextError,
    PdfParsingError,
    TextPipelineError,
)
from magi.retrieval.application import VectorIndexError


def processing_failure_from(error: Exception) -> ProcessingFailure:
    if isinstance(error, ObjectStorageError):
        code = ProcessingErrorCode.OBJECT_STORAGE_UNAVAILABLE
    elif isinstance(error, PdfEncryptedError):
        code = ProcessingErrorCode.PDF_ENCRYPTED
    elif isinstance(error, (PdfNoExtractableTextError, NoTextContentError)):
        code = ProcessingErrorCode.NO_EXTRACTABLE_TEXT
    elif isinstance(error, ContentBlockTooLargeError):
        code = ProcessingErrorCode.CONTENT_BLOCK_TOO_LARGE
    elif isinstance(error, EmbeddingProviderUnavailableError):
        code = ProcessingErrorCode.EMBEDDING_PROVIDER_UNAVAILABLE
    elif isinstance(error, EmbeddingResponseInvalidError):
        code = ProcessingErrorCode.EMBEDDING_RESPONSE_INVALID
    elif isinstance(error, VectorIndexError):
        code = ProcessingErrorCode.VECTOR_INDEX_UNAVAILABLE
    elif isinstance(error, (PdfParsingError, InvalidTextEncodingError, TextPipelineError)):
        code = ProcessingErrorCode.PARSING_FAILED
    else:
        code = ProcessingErrorCode.PROCESSING_FAILED
    return ProcessingFailure(code=code, message="Document processing failed")
