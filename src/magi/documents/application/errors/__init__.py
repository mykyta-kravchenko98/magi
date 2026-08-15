"""Documents application errors."""

from magi.documents.application.errors.base import DocumentApplicationError
from magi.documents.application.errors.object_storage import (
    ObjectAlreadyExistsError,
    ObjectStorageError,
)
from magi.documents.application.errors.resource import (
    DocumentAdditionNotFoundError,
    KnowledgeBaseNotActiveError,
    KnowledgeBaseNotFoundError,
)
from magi.documents.application.errors.upload_validation import (
    EmptyUploadError,
    InvalidUploadContentError,
    UnsupportedUploadMediaTypeError,
    UploadTooLargeError,
    UploadValidationError,
)

__all__ = [
    "DocumentAdditionNotFoundError",
    "DocumentApplicationError",
    "EmptyUploadError",
    "InvalidUploadContentError",
    "KnowledgeBaseNotActiveError",
    "KnowledgeBaseNotFoundError",
    "ObjectAlreadyExistsError",
    "ObjectStorageError",
    "UnsupportedUploadMediaTypeError",
    "UploadTooLargeError",
    "UploadValidationError",
]
