"""Errors raised when an upload is rejected before acceptance."""

from magi.documents.application.errors.base import DocumentApplicationError


class UploadValidationError(DocumentApplicationError):
    """The upload was rejected before a document addition was created."""


class EmptyUploadError(UploadValidationError):
    """The uploaded file has no bytes."""


class UploadTooLargeError(UploadValidationError):
    """The uploaded file exceeds the configured limit."""


class UnsupportedUploadMediaTypeError(UploadValidationError):
    """The declared media type or filename extension is unsupported."""


class InvalidUploadContentError(UploadValidationError):
    """The uploaded bytes do not match the declared supported format."""
