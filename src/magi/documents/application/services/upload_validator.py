"""Pre-acceptance validation for supported document uploads."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from magi.documents.application.errors import (
    EmptyUploadError,
    InvalidUploadContentError,
    UnsupportedUploadMediaTypeError,
    UploadTooLargeError,
)
from magi.documents.application.models import ValidatedUpload

if TYPE_CHECKING:
    from magi.documents.application.commands import UploadDocumentCommand

_EXTENSIONS = {
    "application/pdf": frozenset({".pdf"}),
    "text/plain": frozenset({".txt"}),
    "text/markdown": frozenset({".md", ".markdown"}),
}


class UploadValidator:
    def __init__(self, max_upload_bytes: int) -> None:
        if max_upload_bytes < 1:
            raise ValueError("max_upload_bytes must be positive")
        self._max_upload_bytes = max_upload_bytes

    def validate(self, command: UploadDocumentCommand) -> ValidatedUpload:
        if not command.content:
            raise EmptyUploadError("uploaded file is empty")
        if len(command.content) > self._max_upload_bytes:
            raise UploadTooLargeError("uploaded file exceeds the configured limit")
        filename = PurePosixPath(command.filename.replace("\\", "/")).name.strip()
        if not filename or filename in {".", ".."}:
            raise UnsupportedUploadMediaTypeError("filename is required")
        parts = [part.strip().lower() for part in command.media_type.split(";")]
        media_type = parts[0]
        parameters = parts[1:]
        if media_type not in _EXTENSIONS:
            raise UnsupportedUploadMediaTypeError("unsupported media type")
        if PurePosixPath(filename).suffix.lower() not in _EXTENSIONS[media_type]:
            raise UnsupportedUploadMediaTypeError("filename extension does not match media type")
        if parameters and not (
            media_type.startswith("text/")
            and all(parameter in {"charset=utf-8", 'charset="utf-8"'} for parameter in parameters)
        ):
            raise UnsupportedUploadMediaTypeError("unsupported media type parameter")
        if media_type == "application/pdf":
            if not command.content.startswith(b"%PDF-"):
                raise InvalidUploadContentError("content is not a PDF file")
        else:
            try:
                command.content.decode("utf-8", errors="strict")
            except UnicodeDecodeError as error:
                raise InvalidUploadContentError("text upload must be UTF-8") from error
        return ValidatedUpload(filename=filename, media_type=media_type)
