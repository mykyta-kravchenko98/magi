"""HTTP adapter for the Qdrant vector index."""

import math
from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import cast
from uuid import UUID, uuid5

import httpx

from magi.retrieval.application.errors import (
    VectorIndexConfigurationError,
    VectorIndexUnavailableError,
    VectorPointInvalidError,
)
from magi.retrieval.application.value_objects import VectorPoint
from magi.retrieval.infrastructure.vector_index.config import QdrantVectorIndexConfig


def deterministic_point_id(document_version_id: UUID, chunk_index: int) -> UUID:
    """Derive a stable point ID from the immutable chunk identity."""
    if chunk_index < 0:
        raise ValueError("chunk_index must be non-negative")
    return uuid5(document_version_id, f"chunk:{chunk_index}")


def _json_object(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise VectorIndexUnavailableError(f"{context} response must be a JSON object")
    return cast("Mapping[str, object]", value)


class QdrantVectorIndex:
    """Store retrieval-owned chunk projections using deterministic point IDs."""

    def __init__(
        self,
        config: QdrantVectorIndexConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._owns_client = client is None
        headers = {"api-key": config.api_key} if config.api_key else None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout_seconds),
            headers=headers,
        )

    async def __aenter__(self) -> "QdrantVectorIndex":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def ensure_collection(self) -> str:
        path = f"/collections/{self._config.collection_name}"
        response = await self._request("GET", path)
        if response.status_code == 404:
            response = await self._request(
                "PUT",
                path,
                json={
                    "vectors": {
                        "size": self._config.vector_dimension,
                        "distance": self._config.distance,
                    }
                },
            )
            if response.status_code == 409:
                response = await self._request("GET", path)
            else:
                self._raise_for_status(response)
                self._validate_operation(response, "create collection")
                return self._config.collection_name

        self._raise_for_status(response)
        self._validate_collection(response)
        return self._config.collection_name

    async def upsert(self, points: Sequence[VectorPoint]) -> int:
        point_batch = tuple(points)
        self._validate_points(point_batch)
        path = f"/collections/{self._config.collection_name}/points"
        for start in range(0, len(point_batch), self._config.batch_size):
            batch = point_batch[start : start + self._config.batch_size]
            response = await self._request(
                "PUT",
                path,
                params={"wait": "true"},
                json={"points": [self._point_record(point) for point in batch]},
            )
            self._raise_for_status(response)
            self._validate_operation(response, "upsert points")
        return len(point_batch)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        json: object | None = None,
    ) -> httpx.Response:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        try:
            return await self._client.request(method, url, params=params, json=json)
        except httpx.HTTPError as error:
            raise VectorIndexUnavailableError("Qdrant request failed") from error

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise VectorIndexUnavailableError(
                f"Qdrant returned HTTP {response.status_code}"
            ) from error

    def _validate_collection(self, response: httpx.Response) -> None:
        payload = self._response_object(response, "collection info")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise VectorIndexUnavailableError("Qdrant collection info has no result object")
        result_object = cast("Mapping[str, object]", result)
        raw_config = result_object.get("config")
        config = cast("Mapping[str, object]", raw_config) if isinstance(raw_config, dict) else None
        raw_params = config.get("params") if config is not None else None
        params = cast("Mapping[str, object]", raw_params) if isinstance(raw_params, dict) else None
        raw_vectors = params.get("vectors") if params is not None else None
        vectors = (
            cast("Mapping[str, object]", raw_vectors) if isinstance(raw_vectors, dict) else None
        )
        if vectors is None:
            raise VectorIndexConfigurationError(
                "Qdrant collection must use one unnamed dense vector"
            )
        size = vectors.get("size")
        distance = vectors.get("distance")
        if size != self._config.vector_dimension or distance != self._config.distance:
            raise VectorIndexConfigurationError(
                "Qdrant collection vector size or distance does not match configuration"
            )

    def _validate_operation(self, response: httpx.Response, context: str) -> None:
        payload = self._response_object(response, context)
        if payload.get("status") != "ok":
            raise VectorIndexUnavailableError(f"Qdrant {context} was not acknowledged")
        result = payload.get("result")
        if isinstance(result, bool):
            if not result:
                raise VectorIndexUnavailableError(f"Qdrant {context} failed")
            return
        if (
            not isinstance(result, dict)
            or cast("Mapping[str, object]", result).get("status") != "completed"
        ):
            raise VectorIndexUnavailableError(f"Qdrant {context} did not complete")

    @staticmethod
    def _response_object(response: httpx.Response, context: str) -> Mapping[str, object]:
        try:
            payload = cast("object", response.json())
        except ValueError as error:
            raise VectorIndexUnavailableError(f"Qdrant {context} returned invalid JSON") from error
        return _json_object(payload, context)

    def _validate_points(self, points: Sequence[VectorPoint]) -> None:
        identities: set[tuple[UUID, int]] = set()
        for point in points:
            identity = (point.document_version_id, point.chunk_index)
            if identity in identities:
                raise VectorPointInvalidError("point batch contains duplicate chunk identity")
            identities.add(identity)
            if len(point.vector) != self._config.vector_dimension:
                raise VectorPointInvalidError(
                    f"point vector dimension must be {self._config.vector_dimension}"
                )
            raw_vector = cast("tuple[object, ...]", point.vector)
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in raw_vector
            ):
                raise VectorPointInvalidError("point vector values must be finite numbers")

    @staticmethod
    def _point_record(point: VectorPoint) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "knowledge_base_id": str(point.knowledge_base_id),
            "document_id": str(point.document_id),
            "document_version_id": str(point.document_version_id),
            "chunk_index": point.chunk_index,
            "content_type": point.content_type,
            "heading_path": list(point.heading_path),
            "text": point.text,
        }
        if point.page_start is not None:
            payload["page_start"] = point.page_start
            payload["page_end"] = point.page_end
        return {
            "id": str(deterministic_point_id(point.document_version_id, point.chunk_index)),
            "vector": list(point.vector),
            "payload": payload,
        }
