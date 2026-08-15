"""Immutable object-storage port."""

from typing import Protocol


class ObjectStorage(Protocol):
    async def put(
        self,
        *,
        object_key: str,
        content: bytes,
        media_type: str,
    ) -> str: ...
