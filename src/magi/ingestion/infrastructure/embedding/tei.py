"""HTTP adapter for Hugging Face Text Embeddings Inference."""

import asyncio
import math
from collections.abc import Mapping, Sequence
from typing import Any, cast

import httpx

from magi.ingestion.application.errors import (
    EmbeddingProviderUnavailableError,
    EmbeddingResponseInvalidError,
)
from magi.ingestion.application.models import EmbeddingBatch, EmbeddingModelMetadata
from magi.ingestion.infrastructure.embedding.config import TeiEmbeddingConfig


def _json_object(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise EmbeddingResponseInvalidError(f"{context} response must be a JSON object")
    return cast("Mapping[str, object]", value)


class TeiEmbeddingProvider:
    """Generate ordered embeddings in bounded client-side batches."""

    def __init__(
        self,
        config: TeiEmbeddingConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._owns_client = client is None
        headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout_seconds),
            headers=headers,
        )
        self._metadata: EmbeddingModelMetadata | None = None
        self._metadata_lock = asyncio.Lock()

    async def __aenter__(self) -> "TeiEmbeddingProvider":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        del exc_type, exc_value, traceback
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def embed(self, inputs: Sequence[str]) -> EmbeddingBatch:
        texts = tuple(inputs)
        if any(not text.strip() for text in texts):
            raise ValueError("embedding inputs must be non-blank strings")
        metadata = await self._model_metadata()
        vectors: list[tuple[float, ...]] = []
        for start in range(0, len(texts), self._config.batch_size):
            batch = texts[start : start + self._config.batch_size]
            payload = await self._request_json(
                "POST",
                "/embed",
                json={"inputs": list(batch), "truncate": False},
            )
            vectors.extend(self._parse_vectors(payload, expected_count=len(batch)))
        return EmbeddingBatch(vectors=tuple(vectors), model=metadata)

    async def _model_metadata(self) -> EmbeddingModelMetadata:
        if self._metadata is not None:
            return self._metadata
        async with self._metadata_lock:
            if self._metadata is not None:
                return self._metadata
            payload = _json_object(await self._request_json("GET", "/info"), "TEI info")
            model_id = payload.get("model_id")
            revision = payload.get("model_sha")
            if model_id != self._config.model_id:
                raise EmbeddingResponseInvalidError(
                    f"TEI model_id mismatch: expected {self._config.model_id!r}"
                )
            if revision != self._config.model_revision:
                raise EmbeddingResponseInvalidError(
                    "TEI model revision does not match the configured embedding profile"
                )
            self._metadata = EmbeddingModelMetadata(
                model_id=self._config.model_id,
                model_revision=self._config.model_revision,
                vector_dimension=self._config.vector_dimension,
            )
            return self._metadata

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: object | None = None,
    ) -> object:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        try:
            response = await self._client.request(method, url, json=json)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise EmbeddingProviderUnavailableError("embedding server request failed") from error
        try:
            return cast("object", response.json())
        except ValueError as error:
            raise EmbeddingResponseInvalidError("embedding server returned invalid JSON") from error

    def _parse_vectors(
        self,
        payload: object,
        *,
        expected_count: int,
    ) -> tuple[tuple[float, ...], ...]:
        if not isinstance(payload, list):
            raise EmbeddingResponseInvalidError(
                f"embedding count mismatch: expected {expected_count}"
            )
        raw_vectors = cast("list[object]", payload)
        if len(raw_vectors) != expected_count:
            raise EmbeddingResponseInvalidError(
                f"embedding count mismatch: expected {expected_count}"
            )
        vectors: list[tuple[float, ...]] = []
        for raw_vector in raw_vectors:
            if not isinstance(raw_vector, list):
                raise EmbeddingResponseInvalidError(
                    f"embedding dimension must be {self._config.vector_dimension}"
                )
            raw_values = cast("list[object]", raw_vector)
            if len(raw_values) != self._config.vector_dimension:
                raise EmbeddingResponseInvalidError(
                    f"embedding dimension must be {self._config.vector_dimension}"
                )
            vector: list[float] = []
            for raw_value in cast("list[Any]", raw_values):
                if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                    raise EmbeddingResponseInvalidError("embedding values must be numeric")
                value = float(raw_value)
                if not math.isfinite(value):
                    raise EmbeddingResponseInvalidError("embedding values must be finite")
                vector.append(value)
            vectors.append(tuple(vector))
        return tuple(vectors)
