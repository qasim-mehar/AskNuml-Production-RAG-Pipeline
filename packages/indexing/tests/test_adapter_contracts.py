"""The shared port contracts run against the real adapters, not just fakes (L12)."""

from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone

import pytest
from qdrant_client import QdrantClient

from tests.contracts.port_contracts import (
    assert_object_store_contract,
    assert_vector_payload_roundtrip_contract,
    assert_vector_store_contract,
)
from tests.factories import FIXED_TIME
from uni_rag_core import Chunk, ConfigError, FakeClock, load_settings
from uni_rag_core.fakes.vector_store import OPERATIONAL_FIELDS
from uni_rag_indexing.adapters.minio_object_store import MinioObjectStore
from uni_rag_indexing.adapters.qdrant_vector_store import (
    OPERATIONAL_FIELDS as QDRANT_OPERATIONAL_FIELDS,
)
from uni_rag_indexing.adapters.qdrant_vector_store import (
    QdrantVectorStore,
)
from uni_rag_indexing.domain.filters import point_id
from uni_rag_indexing.domain.payload_index import PayloadVectorIndex

VECTOR = [1.0] + [0.0] * 15


def _qdrant_reachable() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("localhost", 6333)) == 0


def test_qdrant_adapter_passes_vector_store_contract(qdrant_contract: QdrantVectorStore) -> None:
    assert_vector_store_contract(qdrant_contract)


def test_qdrant_adapter_passes_vector_payload_roundtrip_contract(
    qdrant_contract: QdrantVectorStore,
) -> None:
    """ADR 0010: local-mode Qdrant returns lossless, domain-clean Chunk payloads."""
    assert_vector_payload_roundtrip_contract(qdrant_contract)


def test_qdrant_strip_removes_exactly_the_operational_fields(
    qdrant_local: QdrantVectorStore, base_chunk: Chunk
) -> None:
    """All nine predicates stay stored; every Chunk field, metadata included, is returned."""
    assert QDRANT_OPERATIONAL_FIELDS == frozenset(OPERATIONAL_FIELDS)
    qdrant_local.upsert([(base_chunk, VECTOR)])
    hits = qdrant_local.search(VECTOR, top_k=1)
    assert len(hits) == 1

    stored = qdrant_local._client.retrieve(
        collection_name="chunks_dense", ids=[point_id(base_chunk)], with_payload=True
    )
    assert len(stored) == 1
    stored_payload = stored[0].payload or {}
    assert set(OPERATIONAL_FIELDS) <= set(stored_payload)

    assert not set(OPERATIONAL_FIELDS) & set(hits[0].payload)
    assert hits[0].payload == base_chunk.model_dump(mode="json")
    assert hits[0].payload["metadata"] == base_chunk.metadata


def test_qdrant_roundtrip_preserves_non_utc_timestamp_offset(
    qdrant_local: QdrantVectorStore, base_chunk: Chunk
) -> None:
    """Losslessness (ADR 0010) includes the original timezone offset (L4/L6)."""
    shifted = base_chunk.model_copy(
        update={"last_crawled": datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=2)))}
    )
    qdrant_local.upsert([(shifted, VECTOR)])
    assert qdrant_local.search(VECTOR, top_k=1)[0].payload == shifted.model_dump(mode="json")


def test_qdrant_reupsert_with_new_metadata_is_not_skipped(
    qdrant_local: QdrantVectorStore, base_chunk: Chunk
) -> None:
    """Idempotency applies to identical chunks; changed metadata must be stored (L4)."""
    qdrant_local.upsert([(base_chunk, VECTOR)])
    changed = base_chunk.model_copy(update={"metadata": {"producer": "chunker-v3"}})
    qdrant_local.upsert([(changed, VECTOR)])
    qdrant_local.upsert([(changed, VECTOR)])  # identical replay stays a single point
    assert qdrant_local.search(VECTOR, top_k=1)[0].payload == changed.model_dump(mode="json")
    stored = qdrant_local._client.retrieve(
        collection_name="chunks_dense", ids=[point_id(changed)], with_payload=True
    )
    assert len(stored) == 1


def test_qdrant_department_pushdown_survives_the_return_path_strip(
    qdrant_local: QdrantVectorStore, corpus: list[Chunk]
) -> None:
    """The strip is return-path only: stored filter predicates still select rows."""
    qdrant_local.upsert([(chunk, VECTOR) for chunk in corpus])
    hits = qdrant_local.search(VECTOR, top_k=10, filters={"department": "cs"})
    assert {hit.chunk_id for hit in hits} == {"chunk-1", "chunk-2", "chunk-3"}
    assert all(not set(OPERATIONAL_FIELDS) & set(hit.payload) for hit in hits)


def test_qdrant_sparse_hits_are_domain_clean(
    qdrant_local: QdrantVectorStore, base_chunk: Chunk
) -> None:
    """The sparse path returns through the same port, so it strips identically."""
    qdrant_local.upsert_sparse(base_chunk, indices=[0, 1], values=[0.9, 0.4])
    hits = qdrant_local.search_sparse(indices=[0, 1], values=[0.9, 0.4], top_k=1)
    assert len(hits) == 1
    assert not set(OPERATIONAL_FIELDS) & set(hits[0].payload)
    assert hits[0].payload == base_chunk.model_dump(mode="json")


@pytest.mark.integration
def test_qdrant_live_adapter_passes_vector_payload_roundtrip_contract() -> None:
    """ADR 0010 also holds against compose Qdrant when the service is reachable."""
    if not _qdrant_reachable():
        pytest.skip("qdrant compose service unreachable on :6333")
    try:
        settings = load_settings()
    except ConfigError as exc:
        pytest.skip(f"settings unavailable: {exc}")
    client = QdrantClient(url=settings.qdrant_url, timeout=10)
    collections = ("contract_roundtrip_dense", "contract_roundtrip_sparse")
    store = QdrantVectorStore(
        client,
        dimension=2,
        dense_collection=collections[0],
        sparse_collection=collections[1],
        clock=FakeClock(FIXED_TIME),
    )
    try:
        assert_vector_payload_roundtrip_contract(store)
    finally:
        for collection in collections:
            if client.collection_exists(collection):
                client.delete_collection(collection)


def test_payload_index_passes_vector_store_contract(payload_index: PayloadVectorIndex) -> None:
    assert_vector_store_contract(payload_index)


def test_minio_adapter_passes_object_store_contract(minio_store: MinioObjectStore) -> None:
    assert_object_store_contract(minio_store)
