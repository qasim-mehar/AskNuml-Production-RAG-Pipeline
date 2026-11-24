"""The shared port contracts run against the real adapters, not just fakes (L12)."""

from __future__ import annotations

from tests.contracts.port_contracts import (
    assert_object_store_contract,
    assert_vector_store_contract,
)
from uni_rag_indexing.adapters.minio_object_store import MinioObjectStore
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore
from uni_rag_indexing.domain.payload_index import PayloadVectorIndex


def test_qdrant_adapter_passes_vector_store_contract(qdrant_contract: QdrantVectorStore) -> None:
    assert_vector_store_contract(qdrant_contract)


def test_payload_index_passes_vector_store_contract(payload_index: PayloadVectorIndex) -> None:
    assert_vector_store_contract(payload_index)


def test_minio_adapter_passes_object_store_contract(minio_store: MinioObjectStore) -> None:
    assert_object_store_contract(minio_store)
