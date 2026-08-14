"""Infrastructure adapters owned by the documents context."""

from magi.documents.infrastructure.object_storage import MinioObjectStorage, create_minio_client

__all__ = ["MinioObjectStorage", "create_minio_client"]
