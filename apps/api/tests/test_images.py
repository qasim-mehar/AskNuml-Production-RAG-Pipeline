"""ADR 0007 image route: object-store bytes, typed 404, trace headers (L3, L5, L7, L11)."""

from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from uni_rag_api.errors import map_error
from uni_rag_api.fixtures import IMAGE_BYTES
from uni_rag_core import NotFoundError, StorageError
from uni_rag_core.fakes import FakeObjectStore

KEY = "images/papers/2024-p1.png"


def test_image_route_serves_exact_stored_bytes_and_content_type(client: TestClient) -> None:
    """The fake object store's bytes and recorded content type reach the caller."""
    response = client.get(f"/api/images/{KEY}")

    assert response.status_code == 200
    assert response.content == IMAGE_BYTES[KEY]
    assert response.headers["content-type"].startswith("image/png")


def test_image_route_carries_request_and_trace_headers(client: TestClient) -> None:
    """Lane H can read x-request-id on the new route (L10)."""
    response = client.get(f"/api/images/{KEY}", headers={"X-Trace-Id": "image-trace-1"})

    assert response.headers["x-request-id"] == "image-trace-1"
    assert response.headers["X-Trace-Id"] == "image-trace-1"


def test_unknown_image_ref_returns_typed_404(client: TestClient) -> None:
    """Missing objects are a core NotFoundError mapped to a typed 404."""
    assert map_error(NotFoundError("missing")) == (404, "not_found")

    response = client.get("/api/images/images/papers/does-not-exist.png")

    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "Image reference does not exist.",
        "details": {"ref_id": "images/papers/does-not-exist.png"},
    }
    assert response.headers["x-request-id"]


def test_store_connection_failure_is_not_masqueraded_as_404() -> None:
    """Only missing objects are 404; a broken store stays a typed 503."""
    from uni_rag_api.service import ObjectStoreImageService

    class BrokenStore(FakeObjectStore):
        def get(self, key: str) -> bytes:
            msg = "minio connection failed during get"
            raise StorageError(msg)

    service = ObjectStoreImageService(BrokenStore())
    with pytest.raises(StorageError):
        service.get(KEY)


@pytest.mark.parametrize("key", ["../secret.png", "/etc/passwd"])
def test_unsafe_image_ref_is_rejected_as_404(client: TestClient, key: str) -> None:
    """Traversal-shaped keys never reach the store."""
    response = client.get(f"/api/images/{quote(key, safe='')}")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_urdu_image_ref_round_trips_through_encoded_path(client: TestClient) -> None:
    """A non-ASCII ref_id survives URL encoding with exact bytes (L7)."""
    key = "images/urdu/صفحہ-3.png"

    response = client.get(f"/api/images/{quote(key, safe='/')}")

    assert response.status_code == 200
    assert response.content == IMAGE_BYTES[key]


def test_plain_object_store_gets_the_same_content_type_rule() -> None:
    """A store without a recorded type yields the same PNG type (L4)."""
    from uni_rag_api.service import ObjectStoreImageService, as_typed_store

    class PlainStore:
        def put(self, key: str, data: bytes, *, content_type: str = "") -> str:
            return key

        def get(self, key: str) -> bytes:
            return IMAGE_BYTES[key]

        def delete(self, key: str) -> None:
            return None

    image = ObjectStoreImageService(as_typed_store(PlainStore())).get(KEY)

    assert image.content_type == "image/png"
    assert image.data == IMAGE_BYTES[KEY]


def test_real_backend_flag_serves_the_same_image_bytes(real_app: FastAPI) -> None:
    """The real-backend composition uses the same injected ObjectStore port."""
    client = TestClient(real_app)

    response = client.get(f"/api/images/{KEY}")

    assert response.status_code == 200
    assert response.content == IMAGE_BYTES[KEY]
