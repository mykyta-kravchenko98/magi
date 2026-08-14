import json
from collections.abc import Callable
from typing import cast

import httpx
import pytest

from magi.ingestion.application import (
    EmbeddingProvider,
    EmbeddingProviderUnavailableError,
    EmbeddingResponseInvalidError,
)
from magi.ingestion.infrastructure.embedding import TeiEmbeddingConfig, TeiEmbeddingProvider


def config(**overrides: object) -> TeiEmbeddingConfig:
    values: dict[str, object] = {
        "base_url": "http://tei.test",
        "model_id": "model/test",
        "model_revision": "revision-1",
        "vector_dimension": 3,
        "batch_size": 2,
        "timeout_seconds": 1.0,
    }
    values.update(overrides)
    return TeiEmbeddingConfig(**values)  # pyright: ignore[reportArgumentType]


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_embed_batches_inputs_and_preserves_response_order() -> None:
    requests: list[tuple[str, str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = cast("object", json.loads(request.content)) if request.content else None
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/info":
            return httpx.Response(
                200,
                json={"model_id": "model/test", "model_sha": "revision-1"},
            )
        assert isinstance(body, dict)
        body_object = cast("dict[str, object]", body)
        inputs = body_object["inputs"]
        assert isinstance(inputs, list)
        text_inputs = cast("list[str]", inputs)
        return httpx.Response(
            200,
            json=[[float(text.removeprefix("text-")), 1.0, 2.0] for text in text_inputs],
        )

    async with client_for(handler) as client:
        provider = TeiEmbeddingProvider(config(), client=client)
        port: EmbeddingProvider = provider
        result = await port.embed(["text-0", "text-1", "text-2", "text-3", "text-4"])
        await port.embed([])

    assert result.vectors == (
        (0.0, 1.0, 2.0),
        (1.0, 1.0, 2.0),
        (2.0, 1.0, 2.0),
        (3.0, 1.0, 2.0),
        (4.0, 1.0, 2.0),
    )
    assert result.model.model_id == "model/test"
    assert result.model.model_revision == "revision-1"
    assert result.model.vector_dimension == 3
    assert [request[:2] for request in requests] == [
        ("GET", "/info"),
        ("POST", "/embed"),
        ("POST", "/embed"),
        ("POST", "/embed"),
    ]
    assert [request[2] for request in requests[1:]] == [
        {"inputs": ["text-0", "text-1"], "truncate": False},
        {"inputs": ["text-2", "text-3"], "truncate": False},
        {"inputs": ["text-4"], "truncate": False},
    ]


@pytest.mark.parametrize(
    ("info", "message"),
    [
        ({"model_id": "other", "model_sha": "revision-1"}, "model_id mismatch"),
        ({"model_id": "model/test", "model_sha": "other"}, "revision"),
    ],
)
async def test_embed_rejects_wrong_model_identity(
    info: dict[str, str],
    message: str,
) -> None:
    async with client_for(lambda _request: httpx.Response(200, json=info)) as client:
        provider = TeiEmbeddingProvider(config(), client=client)
        with pytest.raises(EmbeddingResponseInvalidError, match=message):
            await provider.embed(["text"])


@pytest.mark.parametrize(
    "payload",
    [
        [],
        [[1.0, 2.0]],
        [[1.0, 2.0, "bad"]],
        [[1.0, 2.0, True]],
    ],
)
async def test_embed_rejects_invalid_vectors(payload: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/info":
            return httpx.Response(
                200,
                json={"model_id": "model/test", "model_sha": "revision-1"},
            )
        return httpx.Response(200, json=payload)

    async with client_for(handler) as client:
        provider = TeiEmbeddingProvider(config(), client=client)
        with pytest.raises(EmbeddingResponseInvalidError):
            await provider.embed(["text"])


async def test_embed_rejects_non_finite_vector_value() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/info":
            return httpx.Response(
                200,
                json={"model_id": "model/test", "model_sha": "revision-1"},
            )
        return httpx.Response(
            200,
            content=b"[[1.0, 2.0, Infinity]]",
            headers={"content-type": "application/json"},
        )

    async with client_for(handler) as client:
        provider = TeiEmbeddingProvider(config(), client=client)
        with pytest.raises(EmbeddingResponseInvalidError, match="finite"):
            await provider.embed(["text"])


async def test_embed_translates_timeout_to_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with client_for(handler) as client:
        provider = TeiEmbeddingProvider(config(), client=client)
        with pytest.raises(EmbeddingProviderUnavailableError, match="request failed"):
            await provider.embed(["text"])


async def test_embed_rejects_blank_input_before_request() -> None:
    async with client_for(lambda _request: httpx.Response(500)) as client:
        provider = TeiEmbeddingProvider(config(), client=client)
        with pytest.raises(ValueError, match="non-blank"):
            await provider.embed([" "])


@pytest.mark.parametrize(
    "overrides",
    [
        {"base_url": "tei.test"},
        {"model_id": " "},
        {"model_revision": " "},
        {"vector_dimension": 0},
        {"batch_size": 0},
        {"timeout_seconds": 0},
    ],
)
def test_embedding_config_rejects_invalid_values(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        config(**overrides)
