"""Application-owned embedding provider port."""

from collections.abc import Sequence
from typing import Protocol

from magi.ingestion.application.models import EmbeddingBatch


class EmbeddingProvider(Protocol):
    async def embed(self, inputs: Sequence[str]) -> EmbeddingBatch: ...
