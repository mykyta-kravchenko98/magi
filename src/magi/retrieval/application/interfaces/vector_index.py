"""Application-owned vector index port."""

from collections.abc import Sequence
from typing import Protocol

from magi.retrieval.application.models import VectorPoint


class VectorIndex(Protocol):
    async def ensure_collection(self) -> str: ...

    async def upsert(self, points: Sequence[VectorPoint]) -> int: ...
