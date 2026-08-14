"""Immutable object-storage interface and its application-owned errors."""

from typing import Protocol


class ObjectStorage(Protocol):
    async def put(
        self,
        *,
        object_key: str,
        content: bytes,
        media_type: str,
    ) -> str: ...


class ObjectStorageError(Exception):
    """An object-storage operation could not be completed."""


class ObjectAlreadyExistsError(ObjectStorageError):
    """An immutable object key is already occupied."""
