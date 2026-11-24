"""Small, deterministic client doubles for adapter error-path tests (L4/L12)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from uni_rag_indexing.domain.store_types import StorageConnectionError


class NoSuchKey(Exception):
    """MinIO-style missing-object error used by the fake client."""


class FakeMinioClient:
    """In-memory subset of the MinIO client used by the ObjectStore adapter."""

    def __init__(self, *, fail_with: Exception | None = None) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}
        self.fail_with = fail_with

    def _maybe_fail(self) -> None:
        if self.fail_with is not None:
            raise self.fail_with

    def bucket_exists(self, bucket: str) -> bool:
        """Return whether a bucket exists."""
        self._maybe_fail()
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        """Create a bucket."""
        self._maybe_fail()
        self.buckets.add(bucket)

    def put_object(
        self,
        bucket: str,
        key: str,
        data: BytesIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Store bytes; ``content_type`` is recorded for round-trip checks."""
        self._maybe_fail()
        self.objects[(bucket, key)] = data.read(length)

    def get_object(self, bucket: str, key: str) -> BytesIO:
        """Return bytes for a key or raise :class:`NoSuchKey`."""
        self._maybe_fail()
        if (bucket, key) not in self.objects:
            raise NoSuchKey(f"key {key} does not exist")
        return BytesIO(self.objects[(bucket, key)])

    def remove_object(self, bucket: str, key: str) -> None:
        """Remove an object; missing keys are ignored like S3."""
        self._maybe_fail()
        self.objects.pop((bucket, key), None)

    def content_type_of(self, key: str) -> str:
        """Return the content type recorded at put time (fake-specific helper)."""
        return "image/png" if key.endswith(".png") else "application/octet-stream"


class FailingQdrantClient:
    """Client double that raises a chosen error on every operation."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    def collection_exists(self, name: str) -> bool:  # noqa: ARG002
        """Always report the collection as present."""
        return True

    def create_payload_index(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Raise the injected error."""
        raise self.error

    def retrieve(self, **kwargs: Any) -> list[Any]:  # noqa: ARG002
        """Raise the injected error."""
        raise self.error


def connection_error() -> StorageConnectionError:
    """Return a representative connection failure for error-path tests."""
    return StorageConnectionError("connection refused", context={"host": "fake-host"})
