"""MinIO implementation of the documents object-storage port."""

import asyncio
from io import BytesIO

import urllib3
from minio import Minio
from minio.error import MinioException, S3Error
from urllib3.exceptions import HTTPError

from magi.documents.application import ObjectAlreadyExistsError, ObjectStorageError
from magi.shared.config import Settings

_MISSING_OBJECT_CODES = frozenset({"NoSuchKey", "NoSuchObject"})
_BUCKET_RACE_CODES = frozenset({"BucketAlreadyExists", "BucketAlreadyOwnedByYou"})


def create_minio_client(settings: Settings) -> Minio:
    timeout = settings.object_storage_timeout_seconds
    http_client = urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=timeout, read=timeout),
        retries=False,
    )
    return Minio(
        endpoint=settings.object_storage_endpoint,
        access_key=settings.object_storage_access_key,
        secret_key=settings.object_storage_secret_key.get_secret_value(),
        secure=settings.object_storage_secure,
        http_client=http_client,
    )


class MinioObjectStorage:
    def __init__(self, client: Minio, bucket_name: str) -> None:
        self._client = client
        self._bucket_name = bucket_name

    async def put(
        self,
        *,
        object_key: str,
        content: bytes,
        media_type: str,
    ) -> str:
        return await asyncio.to_thread(
            self._put_sync,
            object_key,
            content,
            media_type,
        )

    def _put_sync(self, object_key: str, content: bytes, media_type: str) -> str:
        try:
            self._ensure_bucket()
            if self._object_exists(object_key):
                raise ObjectAlreadyExistsError("immutable object key already exists")
            self._client.put_object(
                bucket_name=self._bucket_name,
                object_name=object_key,
                data=BytesIO(content),
                length=len(content),
                content_type=media_type,
            )
        except ObjectAlreadyExistsError:
            raise
        except (MinioException, HTTPError, OSError) as error:
            raise ObjectStorageError("object storage operation failed") from error
        return object_key

    def _ensure_bucket(self) -> None:
        if self._client.bucket_exists(self._bucket_name):
            return
        try:
            self._client.make_bucket(self._bucket_name)
        except S3Error as error:
            if error.code not in _BUCKET_RACE_CODES:
                raise

    def _object_exists(self, object_key: str) -> bool:
        try:
            self._client.stat_object(self._bucket_name, object_key)
        except S3Error as error:
            if error.code in _MISSING_OBJECT_CODES:
                return False
            raise
        return True
