"""Indexing orchestration: idempotency, version bump, verify and stale cleanup."""

from __future__ import annotations

import pytest

from uni_rag_core import (
    Chunk,
    Embedder,
    FakeClock,
    FakeObjectStore,
    FakeVectorStore,
    ImageRef,
    StorageError,
)
from uni_rag_indexing.domain.metadata_memory import InMemoryMetadataStore
from uni_rag_indexing.domain.payload_index import PayloadVectorIndex
from uni_rag_indexing.domain.store_types import ChunkRecord
from uni_rag_indexing.service.index import IndexingService


def _service(
    vectors: PayloadVectorIndex,
    metadata: InMemoryMetadataStore,
    embedder: Embedder,
    clock: FakeClock,
) -> IndexingService:
    return IndexingService(
        vectors=vectors,
        objects=FakeObjectStore(),
        metadata=metadata,
        embedder=embedder,
        clock=clock,
    )


def test_index_then_replay_changes_nothing(
    corpus: list[Chunk],
    payload_index: PayloadVectorIndex,
    metadata_memory: InMemoryMetadataStore,
    embedder: Embedder,
    fixed_clock: FakeClock,
) -> None:
    service = _service(payload_index, metadata_memory, embedder, fixed_clock)
    first = service.index(corpus)
    assert first.inserted == 4 and first.unchanged == 1 and first.verified == 4
    before = payload_index.payloads()
    history_before = metadata_memory.history_count()

    second = service.index(corpus)
    assert second.unchanged == 5 and second.inserted == 0 and second.updated == 0
    assert payload_index.payloads() == before
    assert metadata_memory.history_count() == history_before


def test_changed_chunk_bumps_version_and_soft_deletes_previous(
    stale_pair: tuple[Chunk, Chunk],
    payload_index: PayloadVectorIndex,
    metadata_memory: InMemoryMetadataStore,
    embedder: Embedder,
    fixed_clock: FakeClock,
) -> None:
    original, changed = stale_pair
    service = _service(payload_index, metadata_memory, embedder, fixed_clock)
    service.index([original])
    result = service.index([changed])

    assert result.updated == 1 and result.stale_soft_deleted == 1 and result.verified == 1
    current = metadata_memory.get_chunk("chunk-5")
    assert current is not None and current.version == "2" and current.is_live
    history = metadata_memory.list_chunk_history("doc-5")
    assert len(history) == 2
    stale = next(item for item in history if item.version == "1")
    assert isinstance(stale, ChunkRecord) and not stale.is_live
    assert stale.superseded_by is not None
    live = payload_index.payloads()
    assert len(live) == 1 and live[0]["version"] == "2"
    assert payload_index.payloads(include_stale=True)[0]["is_live"] is False


def test_reindex_document_soft_deletes_disappeared_chunks(
    corpus: list[Chunk],
    payload_index: PayloadVectorIndex,
    metadata_memory: InMemoryMetadataStore,
    embedder: Embedder,
    fixed_clock: FakeClock,
) -> None:
    service = _service(payload_index, metadata_memory, embedder, fixed_clock)
    service.index(corpus)
    service.reindex_document("doc-2", [chunk for chunk in corpus if chunk.doc_id != "doc-2"])
    assert "chunk-2" not in metadata_memory.list_live_chunk_ids("doc-2")
    assert any(
        item["chunk_id"] == "chunk-2" and not item["is_live"]
        for item in payload_index.payloads(include_stale=True)
    )


def test_page_image_is_stored_by_content_addressed_key(
    payload_index: PayloadVectorIndex,
    metadata_memory: InMemoryMetadataStore,
    embedder: Embedder,
    fixed_clock: FakeClock,
    base_chunk: Chunk,
) -> None:
    objects = FakeObjectStore()
    service = IndexingService(
        vectors=payload_index,
        objects=objects,
        metadata=metadata_memory,
        embedder=embedder,
        clock=fixed_clock,
    )
    assert base_chunk.image_ref is not None
    ref: ImageRef = base_chunk.image_ref
    key = service.index_page_image(ref, b"\x89PNG\r\n\x1a\n")
    assert key.startswith("images/doc-1/") and objects.get(key) == b"\x89PNG\r\n\x1a\n"


def test_verification_failure_raises_typed_error(
    base_chunk: Chunk,
    payload_index: PayloadVectorIndex,
    metadata_memory: InMemoryMetadataStore,
    embedder: Embedder,
    fixed_clock: FakeClock,
) -> None:
    service = _service(payload_index, metadata_memory, embedder, fixed_clock)
    payload_index.is_present = lambda _chunk_id: False  # type: ignore[method-assign]
    with pytest.raises(StorageError):
        service.index([base_chunk])


def test_verification_falls_back_to_search_for_a_plain_vector_store(
    base_chunk: Chunk,
    metadata_memory: InMemoryMetadataStore,
    embedder: Embedder,
    fixed_clock: FakeClock,
) -> None:
    service = IndexingService(
        vectors=FakeVectorStore(),
        objects=FakeObjectStore(),
        metadata=metadata_memory,
        embedder=embedder,
        clock=fixed_clock,
    )
    assert service.index([base_chunk]).verified == 1
