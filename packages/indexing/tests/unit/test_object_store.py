"""Object-store round-trip, content addressing and typed error branches."""

from __future__ import annotations

import pytest

from uni_rag_indexing.adapters.minio_object_store import MinioObjectStore
from uni_rag_indexing.domain.fakes import FakeMinioClient, NoSuchKey
from uni_rag_indexing.domain.object_keys import content_addressed_key
from uni_rag_indexing.domain.store_types import (
    StorageConnectionError,
    StorageNotFoundError,
)

PAGE = b"\x89PNG\r\n\x1a\npage-bytes"


def test_round_trip_preserves_bytes_and_key_is_content_addressed(
    minio_store: MinioObjectStore,
) -> None:
    key = minio_store.put("images/doc-1/p1.png", PAGE, content_type="image/png")
    assert key == content_addressed_key("images/doc-1/p1.png", PAGE)
    assert key.startswith("images/doc-1/") and key.endswith(".png")
    assert minio_store.get(key) == PAGE
    assert minio_store.put("images/doc-1/p1.png", PAGE, content_type="image/png") == key


def test_different_bytes_produce_different_key(minio_store: MinioObjectStore) -> None:
    first = minio_store.put("images/p.png", PAGE)
    second = minio_store.put("images/p.png", PAGE + b"changed")
    assert first != second


def test_missing_get_raises_typed_not_found(minio_store: MinioObjectStore) -> None:
    with pytest.raises(StorageNotFoundError) as exc:
        minio_store.get("images/missing.png")
    assert exc.value.context["host"] == "minio"


def test_delete_is_idempotent(minio_store: MinioObjectStore) -> None:
    key = minio_store.put("images/p.png", PAGE)
    minio_store.delete(key)
    minio_store.delete(key)
    with pytest.raises(StorageNotFoundError):
        minio_store.get(key)


def test_connection_failure_is_typed_with_host() -> None:
    failing = FakeMinioClient(fail_with=ConnectionError("connection refused"))
    store = MinioObjectStore(
        failing, bucket="uni-rag", host="minio.example.edu", ensure_bucket=False
    )
    with pytest.raises(StorageConnectionError) as exc:
        store.put("images/p.png", PAGE)
    assert exc.value.context["host"] == "minio.example.edu"


def test_missing_key_error_is_not_swallowed() -> None:
    failing = FakeMinioClient(fail_with=NoSuchKey("key does not exist"))
    store = MinioObjectStore(failing, bucket="uni-rag", host="minio", ensure_bucket=False)
    with pytest.raises(StorageNotFoundError):
        store.get("images/p.png")
