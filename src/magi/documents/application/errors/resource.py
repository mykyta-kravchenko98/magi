"""Resource and lifecycle lookup errors."""

from magi.documents.application.errors.base import DocumentApplicationError


class KnowledgeBaseNotFoundError(DocumentApplicationError):
    """The requested knowledge base does not exist."""


class KnowledgeBaseNotActiveError(DocumentApplicationError):
    """The requested knowledge base does not accept uploads."""


class DocumentAdditionNotFoundError(DocumentApplicationError):
    """The requested document addition does not exist."""
