import asyncio
import os
from pathlib import Path
from time import monotonic
from uuid import UUID

import httpx
import pytest

from magi.shared.config import QdrantSettings

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("MAGI_RUN_E2E_TESTS", "").lower() != "true",
        reason="set MAGI_RUN_E2E_TESTS=true to use the complete running stack",
    ),
]

KNOWLEDGE_BASE_ID = UUID("c87d83a0-eac5-4a2c-9b7d-31fbdce39f51")
FIXTURE = Path(__file__).parent / "fixtures" / "walking_skeleton.md"


async def test_real_markdown_upload_becomes_searchable_and_exists_in_qdrant() -> None:
    api_base_url = os.getenv("MAGI_E2E_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    qdrant = QdrantSettings()  # pyright: ignore[reportCallIssue]
    qdrant_headers = (
        {"api-key": qdrant.api_key.get_secret_value()} if qdrant.api_key is not None else None
    )

    async with (
        httpx.AsyncClient(timeout=180.0) as api_client,
        httpx.AsyncClient(timeout=qdrant.timeout_seconds, headers=qdrant_headers) as qdrant_client,
    ):
        with FIXTURE.open("rb") as source:
            upload = await api_client.post(
                f"{api_base_url}/api/v1/knowledge-bases/{KNOWLEDGE_BASE_ID}/documents",
                files={"file": (FIXTURE.name, source, "text/markdown")},
            )
        upload.raise_for_status()
        addition_id = upload.json()["document_addition_id"]

        deadline = monotonic() + 120.0
        payload = upload.json()
        while payload["status"] not in {"COMPLETED", "FAILED"} and monotonic() < deadline:
            await asyncio.sleep(1.0)
            status_response = await api_client.get(
                f"{api_base_url}/api/v1/document-additions/{addition_id}"
            )
            status_response.raise_for_status()
            payload = status_response.json()

        assert payload["status"] == "COMPLETED", payload.get("error")
        assert payload["document_version_status"] == "SEARCHABLE"
        assert payload["indexed_chunk_count"] > 0
        document_version_id = payload["document_version_id"]

        points_response = await qdrant_client.post(
            f"{qdrant.url}/collections/{qdrant.collection}/points/scroll",
            json={
                "filter": {
                    "must": [
                        {
                            "key": "document_version_id",
                            "match": {"value": document_version_id},
                        }
                    ]
                },
                "limit": payload["indexed_chunk_count"] + 1,
                "with_payload": True,
                "with_vector": False,
            },
        )
        points_response.raise_for_status()
        points = points_response.json()["result"]["points"]

    assert len(points) == payload["indexed_chunk_count"]
    assert {point["payload"]["document_version_id"] for point in points} == {document_version_id}
    assert any(
        point["payload"]["heading_path"] == ["Walking Skeleton"]
        and "upload pipeline stores this markdown source" in point["payload"]["text"].lower()
        for point in points
    )
