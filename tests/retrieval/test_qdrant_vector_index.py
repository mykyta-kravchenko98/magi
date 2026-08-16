import json
from collections.abc import Callable
from uuid import UUID

import httpx
import pytest

from magi.retrieval.application import (
    VectorIndex,
    VectorIndexConfigurationError,
    VectorIndexUnavailableError,
    VectorPoint,
    VectorPointInvalidError,
)
from magi.retrieval.infrastructure.vector_index import (
    QdrantVectorIndex,
    QdrantVectorIndexConfig,
    deterministic_point_id,
)

KNOWLEDGE_BASE_ID = UUID("10000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("20000000-0000-0000-0000-000000000002")
VERSION_ID = UUID("30000000-0000-0000-0000-000000000003")


def config(**overrides: object) -> QdrantVectorIndexConfig:
    values: dict[str, object] = {
        "base_url": "http://qdrant.test",
        "collection_name": "chunks_v1",
        "vector_dimension": 3,
        "batch_size": 2,
        "timeout_seconds": 1.0,
    }
    values.update(overrides)
    return QdrantVectorIndexConfig(**values)  # pyright: ignore[reportArgumentType]


def point(index: int, *, vector: tuple[float, ...] = (1.0, 2.0, 3.0)) -> VectorPoint:
    return VectorPoint(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
        document_version_id=VERSION_ID,
        chunk_index=index,
        content_type="text",
        content_role="body",
        heading_path=("Architecture",),
        text=f"chunk {index}",
        vector=vector,
        page_start=1,
        page_end=2,
    )


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def collection_info(*, size: int = 3, distance: str = "Cosine") -> dict[str, object]:
    return {
        "status": "ok",
        "result": {"config": {"params": {"vectors": {"size": size, "distance": distance}}}},
    }


async def test_ensure_collection_accepts_matching_existing_collection() -> None:
    async with client_for(lambda _request: httpx.Response(200, json=collection_info())) as client:
        index = QdrantVectorIndex(config(), client=client)
        port: VectorIndex = index
        assert await port.ensure_collection() == "chunks_v1"


async def test_ensure_collection_creates_missing_collection() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(404, json={"status": {"error": "not found"}})
        return httpx.Response(200, json={"status": "ok", "result": True})

    async with client_for(handler) as client:
        index = QdrantVectorIndex(config(), client=client)
        assert await index.ensure_collection() == "chunks_v1"

    assert [request.method for request in requests] == ["GET", "PUT"]
    assert json.loads(requests[1].content) == {"vectors": {"size": 3, "distance": "Cosine"}}


@pytest.mark.parametrize(
    "response",
    [collection_info(size=4), collection_info(distance="Dot")],
)
async def test_ensure_collection_rejects_incompatible_collection(
    response: dict[str, object],
) -> None:
    async with client_for(lambda _request: httpx.Response(200, json=response)) as client:
        index = QdrantVectorIndex(config(), client=client)
        with pytest.raises(VectorIndexConfigurationError, match="does not match"):
            await index.ensure_collection()


async def test_upsert_batches_points_and_uses_stable_ids_and_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"status": "ok", "result": {"status": "completed"}},
        )

    points = [point(index) for index in range(5)]
    async with client_for(handler) as client:
        index = QdrantVectorIndex(config(), client=client)
        assert await index.upsert(points) == 5
        assert await index.upsert(points) == 5

    assert len(requests) == 6
    assert all(request.url.params["wait"] == "true" for request in requests)
    first_run_records = [
        record for request in requests[:3] for record in json.loads(request.content)["points"]
    ]
    second_run_records = [
        record for request in requests[3:] for record in json.loads(request.content)["points"]
    ]
    assert first_run_records == second_run_records
    assert [record["id"] for record in first_run_records] == [
        str(deterministic_point_id(VERSION_ID, chunk_index)) for chunk_index in range(5)
    ]
    assert first_run_records[0]["payload"] == {
        "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
        "document_id": str(DOCUMENT_ID),
        "document_version_id": str(VERSION_ID),
        "chunk_index": 0,
        "content_type": "text",
        "content_role": "body",
        "heading_path": ["Architecture"],
        "text": "chunk 0",
        "page_start": 1,
        "page_end": 2,
    }


async def test_empty_upsert_makes_no_request() -> None:
    async with client_for(lambda _request: httpx.Response(500)) as client:
        index = QdrantVectorIndex(config(), client=client)
        assert await index.upsert([]) == 0


@pytest.mark.parametrize(
    "points",
    [
        [point(0, vector=(1.0, 2.0))],
        [point(0, vector=(1.0, 2.0, float("nan")))],
        [point(0), point(0)],
    ],
)
async def test_upsert_rejects_invalid_points(points: list[VectorPoint]) -> None:
    async with client_for(lambda _request: httpx.Response(500)) as client:
        index = QdrantVectorIndex(config(), client=client)
        with pytest.raises(VectorPointInvalidError):
            await index.upsert(points)


async def test_qdrant_timeout_is_translated() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with client_for(handler) as client:
        index = QdrantVectorIndex(config(), client=client)
        with pytest.raises(VectorIndexUnavailableError, match="request failed"):
            await index.ensure_collection()


def test_deterministic_point_id_is_stable_and_chunk_specific() -> None:
    assert deterministic_point_id(VERSION_ID, 1) == deterministic_point_id(VERSION_ID, 1)
    assert deterministic_point_id(VERSION_ID, 1) != deterministic_point_id(VERSION_ID, 2)
    with pytest.raises(ValueError, match="non-negative"):
        deterministic_point_id(VERSION_ID, -1)


@pytest.mark.parametrize(
    "overrides",
    [
        {"base_url": "qdrant.test"},
        {"collection_name": "bad/name"},
        {"vector_dimension": 0},
        {"batch_size": 0},
        {"timeout_seconds": 0},
    ],
)
def test_qdrant_config_rejects_invalid_values(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        config(**overrides)
