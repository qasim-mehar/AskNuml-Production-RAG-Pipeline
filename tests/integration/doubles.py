"""Small in-memory doubles used to exercise real adapters without Docker (L4).

These are transport doubles only: the adapter under test is Lane D's real
``MinioObjectStore``, so content addressing and typed errors stay real.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any, BinaryIO


class NoSuchKey(Exception):
    """MinIO-shaped missing-object error."""

    code = "NoSuchKey"


class _ObjectResponse:
    """The small slice of the MinIO response the adapter consumes."""

    def __init__(self, payload: bytes) -> None:
        self._stream: BinaryIO = BytesIO(payload)

    def read(self) -> bytes:
        """Return the remaining object bytes."""
        return self._stream.read()

    def close(self) -> None:
        """Release the in-memory stream."""
        self._stream.close()

    def release_conn(self) -> None:
        """No connection to release for an in-memory double."""


class MemoryMinioClient:
    """A bucket/object store sufficient for the ObjectStore contract suite."""

    def __init__(self) -> None:
        self._buckets: set[str] = set()
        self._objects: dict[tuple[str, str], bytes] = {}

    def bucket_exists(self, bucket: str) -> bool:
        """Return whether a bucket was created."""
        return bucket in self._buckets

    def make_bucket(self, bucket: str) -> None:
        """Create a bucket."""
        self._buckets.add(bucket)

    def put_object(
        self,
        bucket: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Store object bytes; ``length`` and content type are accepted for parity."""
        del length, content_type
        self._objects[(bucket, object_name)] = data.read()

    def get_object(self, bucket: str, object_name: str) -> Any:
        """Return the object, raising a missing-key typed error when absent."""
        payload = self._objects.get((bucket, object_name))
        if payload is None:
            raise NoSuchKey(f"key {object_name} not found")
        return _ObjectResponse(payload)

    def remove_object(self, bucket: str, object_name: str) -> None:
        """Remove an object; removing a missing key is a no-op."""
        self._objects.pop((bucket, object_name), None)
