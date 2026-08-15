"""Public application contracts for document workflows."""

from magi.documents.application.commands import UploadDocumentCommand, UploadDocumentHandler
from magi.documents.application.errors import (
    DocumentAdditionNotFoundError,
    DocumentApplicationError,
    EmptyUploadError,
    InvalidUploadContentError,
    KnowledgeBaseNotActiveError,
    KnowledgeBaseNotFoundError,
    ObjectAlreadyExistsError,
    ObjectStorageError,
    UnsupportedUploadMediaTypeError,
    UploadTooLargeError,
    UploadValidationError,
)
from magi.documents.application.interfaces import (
    DocumentAdditionRepository,
    DocumentRepository,
    DocumentVersionRepository,
    KnowledgeBaseRepository,
    ObjectStorage,
    UnitOfWork,
    UnitOfWorkFactory,
)
from magi.documents.application.models import DocumentAdditionView
from magi.documents.application.queries import (
    GetDocumentAdditionStatusHandler,
    GetDocumentAdditionStatusQuery,
)

__all__ = [
    "DocumentAdditionNotFoundError",
    "DocumentAdditionRepository",
    "DocumentAdditionView",
    "DocumentApplicationError",
    "DocumentRepository",
    "DocumentVersionRepository",
    "EmptyUploadError",
    "GetDocumentAdditionStatusHandler",
    "GetDocumentAdditionStatusQuery",
    "InvalidUploadContentError",
    "KnowledgeBaseNotActiveError",
    "KnowledgeBaseNotFoundError",
    "KnowledgeBaseRepository",
    "ObjectAlreadyExistsError",
    "ObjectStorage",
    "ObjectStorageError",
    "UnitOfWork",
    "UnitOfWorkFactory",
    "UnsupportedUploadMediaTypeError",
    "UploadDocumentCommand",
    "UploadDocumentHandler",
    "UploadTooLargeError",
    "UploadValidationError",
]
