"""Typed connection/conflict/not-found branches never swallow external errors."""

from __future__ import annotations

import pytest

from uni_rag_core import Chunk, ValidationError
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore
from uni_rag_indexing.domain.fakes import FailingQdrantClient
from uni_rag_indexing.domain.filters import translate_filters
from uni_rag_indexing.domain.store_types import StorageConnectionError


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
