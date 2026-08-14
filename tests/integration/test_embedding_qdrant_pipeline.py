import os
from uuid import uuid4

import httpx
import pytest

from magi.ingestion.infrastructure.embedding import TeiEmbeddingConfig, TeiEmbeddingProvider
from magi.retrieval.application import VectorPoint
from magi.retrieval.infrastructure.vector_index import (
    QdrantVectorIndex,
    QdrantVectorIndexConfig,
    deterministic_point_id,
)
from magi.shared.config import EmbeddingSettings, QdrantSettings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("MAGI_RUN_INTEGRATION_TESTS", "").lower() != "true",
        reason="set MAGI_RUN_INTEGRATION_TESTS=true to use external services",
    ),
]


async def test_real_tei_embeddings_are_idempotently_upserted_to_qdrant() -> None:
    embedding_settings = EmbeddingSettings()  # pyright: ignore[reportCallIssue]
    qdrant_settings = QdrantSettings()  # pyright: ignore[reportCallIssue]
    collection_name = f"magi_integration_{uuid4().hex}"
    knowledge_base_id = uuid4()
    document_id = uuid4()
    document_version_id = uuid4()
    texts = (
        "Architecture decisions are immutable records.",
        "Chunk projections can be rebuilt from document versions.",
        "Idempotent writes make retries safe.",
    )
    embedding_config = TeiEmbeddingConfig(
        base_url=embedding_settings.base_url,
        model_id=embedding_settings.model_id,
        model_revision=embedding_settings.model_revision,
        vector_dimension=embedding_settings.vector_dimension,
        batch_size=2,
        timeout_seconds=embedding_settings.timeout_seconds,
        api_key=(
            embedding_settings.api_key.get_secret_value()
            if embedding_settings.api_key is not None
            else None
        ),
    )
    qdrant_config = QdrantVectorIndexConfig(
        base_url=qdrant_settings.url,
        collection_name=collection_name,
        vector_dimension=qdrant_settings.vector_dimension,
        batch_size=2,
        timeout_seconds=qdrant_settings.timeout_seconds,
        api_key=(
            qdrant_settings.api_key.get_secret_value()
            if qdrant_settings.api_key is not None
            else None
        ),
    )
    qdrant_headers = (
        {"api-key": qdrant_config.api_key} if qdrant_config.api_key is not None else None
    )
    assert embedding_settings.vector_dimension == qdrant_settings.vector_dimension

    async with (
        TeiEmbeddingProvider(embedding_config) as embedding_provider,
        QdrantVectorIndex(qdrant_config) as vector_index,
        httpx.AsyncClient(
            timeout=qdrant_settings.timeout_seconds,
            headers=qdrant_headers,
        ) as qdrant_client,
    ):
        try:
            embeddings = await embedding_provider.embed(texts)
            assert len(embeddings.vectors) == len(texts)
            assert all(
                len(vector) == embedding_settings.vector_dimension for vector in embeddings.vectors
            )
            await vector_index.ensure_collection()
            points = [
                VectorPoint(
                    knowledge_base_id=knowledge_base_id,
                    document_id=document_id,
                    document_version_id=document_version_id,
                    chunk_index=index,
                    content_type="text",
                    heading_path=("Integration",),
                    text=text,
                    vector=vector,
                )
                for index, (text, vector) in enumerate(zip(texts, embeddings.vectors, strict=True))
            ]

            assert await vector_index.upsert(points) == len(points)
            assert await vector_index.upsert(points) == len(points)

            count_response = await qdrant_client.post(
                f"{qdrant_settings.url}/collections/{collection_name}/points/count",
                json={"exact": True},
            )
            count_response.raise_for_status()
            assert count_response.json()["result"]["count"] == len(points)

            retrieve_response = await qdrant_client.post(
                f"{qdrant_settings.url}/collections/{collection_name}/points",
                json={
                    "ids": [
                        str(deterministic_point_id(document_version_id, index))
                        for index in range(len(points))
                    ],
                    "with_payload": True,
                    "with_vector": False,
                },
            )
            retrieve_response.raise_for_status()
            stored = retrieve_response.json()["result"]
            stored_texts = {
                item["payload"]["chunk_index"]: item["payload"]["text"] for item in stored
            }
            assert stored_texts == dict(enumerate(texts))
        finally:
            delete_response = await qdrant_client.delete(
                f"{qdrant_settings.url}/collections/{collection_name}"
            )
            if delete_response.status_code != 404:
                delete_response.raise_for_status()
