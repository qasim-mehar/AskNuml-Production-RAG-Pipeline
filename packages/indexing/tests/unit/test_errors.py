"""Typed connection/conflict/not-found branches never swallow external errors."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError
from qdrant_client import models

from uni_rag_core import Chunk, ValidationError
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore
from uni_rag_indexing.domain.fakes import FailingQdrantClient
from uni_rag_indexing.domain.filters import translate_filters
from uni_rag_indexing.domain.store_types import StorageConnectionError

VECTOR = [1.0] + [0.0] * 15


def test_qdrant_connection_failure_carries_host(base_chunk: Chunk) -> None:
    store = QdrantVectorStore(
        FailingQdrantClient(ConnectionError("connection refused")),
        host="qdrant.example.edu",
        ensure=False,
    )
    with pytest.raises(StorageConnectionError) as exc:
        store.upsert([(base_chunk, [1.0])])
    assert exc.value.context["host"] == "qdrant.example.edu"
    assert exc.value.context["operation"] == "upsert"


def test_invalid_filter_is_a_typed_validation_error() -> None:
    with pytest.raises(ValidationError):
        translate_filters({"department": "cs", "bogus": "1"})


def test_malformed_stored_payload_raises_typed_core_error(
    qdrant_local: QdrantVectorStore,
) -> None:
    """Storage decode failures cross the adapter boundary as typed core errors (L11)."""
    malformed_id = "11111111-1111-1111-1111-111111111111"
    qdrant_local._client.upsert(
        collection_name="chunks_dense",
        points=[
            models.PointStruct(
                id=malformed_id,
                vector={"dense": VECTOR},
                payload={"chunk_id": "chunk-malformed", "is_live": True},
            )
        ],
    )

    with pytest.raises(ValidationError) as exc:
        qdrant_local.search(VECTOR, top_k=1)

    assert isinstance(exc.value.__cause__, PydanticValidationError)
    assert exc.value.context["chunk_id"] == "chunk-malformed"
    assert exc.value.context["errors"]
