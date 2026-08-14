import asyncio
import os
from uuid import uuid4

import pytest

from magi.documents.application import ObjectAlreadyExistsError
from magi.documents.infrastructure.object_storage import MinioObjectStorage, create_minio_client
from magi.shared.config import Settings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("MAGI_RUN_INTEGRATION_TESTS", "").lower() != "true",
        reason="set MAGI_RUN_INTEGRATION_TESTS=true to use external services",
    ),
]


async def test_minio_upload_preserves_bytes_and_media_type() -> None:
    settings = Settings()
    client = create_minio_client(settings)
    storage = MinioObjectStorage(client, settings.object_storage_bucket)
    object_key = f"integration/{uuid4()}/document.md"
    content = b"# Architecture\n\nImmutable source content."
    uploaded = False

    try:
        reference = await storage.put(
            object_key=object_key,
            content=content,
            media_type="text/markdown",
        )
        uploaded = True
        response = await asyncio.to_thread(
            client.get_object,
            settings.object_storage_bucket,
            object_key,
        )
        try:
            stored_content = await asyncio.to_thread(response.read)
        finally:
            response.close()
            response.release_conn()

        assert reference == object_key
        assert stored_content == content
        metadata = await asyncio.to_thread(
            client.stat_object,
            settings.object_storage_bucket,
            object_key,
        )
        assert metadata.content_type == "text/markdown"

        with pytest.raises(ObjectAlreadyExistsError):
            await storage.put(
                object_key=object_key,
                content=b"replacement",
                media_type="text/plain",
            )
    finally:
        if uploaded:
            await asyncio.to_thread(
                client.remove_object,
                settings.object_storage_bucket,
                object_key,
            )
