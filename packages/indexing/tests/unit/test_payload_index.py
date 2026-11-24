"""Filter correctness, idempotency and soft delete in deterministic fake mode."""

from __future__ import annotations

from typing import Any

from uni_rag_core import Chunk, Embedder, FakeClock
from uni_rag_indexing.domain.filters import matches_payload, translate_filters
from uni_rag_indexing.domain.payload_index import PayloadVectorIndex


def _vectors(chunks: list[Chunk], embedder: Embedder) -> list[tuple[Chunk, list[float]]]:
    embedded = embedder.embed([chunk.text for chunk in chunks])
    return list(zip(chunks, embedded, strict=True))


def test_filtered_query_returns_exact_matching_count(
    corpus: list[Chunk], embedder: Embedder, payload_index: PayloadVectorIndex
) -> None:
    payload_index.upsert(_vectors(corpus, embedder))
    filters = {"doc_type": "web_page"}
    hits = payload_index.search([1.0] * 16, top_k=10, filters=filters)
    expected = [
        payload["chunk_id"]
        for payload in payload_index.payloads()
        if matches_payload(payload, translate_filters(filters))
    ]
    # The duplicate is the *same* chunk id and content hash, so its
    # content-addressed id collapses it into one stored record (L4).
    assert len(hits) == len(expected) == 1
    assert {hit.chunk_id for hit in hits} == set(expected)

    pdf_hits = payload_index.search([1.0] * 16, top_k=10, filters={"department": "CS"})
    assert {hit.chunk_id for hit in pdf_hits} == {"chunk-1", "chunk-2", "chunk-3"}


def test_double_upsert_leaves_exactly_one_record_and_no_version_bump(
    base_chunk: Chunk, embedder: Embedder, payload_index: PayloadVectorIndex
) -> None:
    once = _vectors([base_chunk], embedder)
    payload_index.upsert(once)
    before = payload_index.payloads()
    payload_index.upsert(once)
    after = payload_index.payloads()
    assert len(after) == 1
    assert before == after
    assert after[0]["version"] == "1"


def test_changed_chunk_soft_deletes_previous_and_hides_it_from_live_queries(
    stale_pair: tuple[Chunk, Chunk],
    embedder: Embedder,
    payload_index: PayloadVectorIndex,
) -> None:
    original, changed = stale_pair
    payload_index.upsert(_vectors([original], embedder))
    payload_index.upsert(_vectors([changed], embedder))

    live = payload_index.payloads()
    history = payload_index.payloads(include_stale=True)
    assert len(live) == 1 and live[0]["version"] == "2"
    assert len(history) == 2
    stale = next(item for item in history if not item["is_live"])
    assert stale["version"] == "1" and stale["deleted_at"] is not None
    hits = payload_index.search([1.0] * 16, top_k=10, filters={"doc_id": "doc-5"})
    assert [hit.chunk_id for hit in hits] == ["chunk-5"]


def test_delete_is_a_soft_delete(
    later_clock: FakeClock, corpus: list[Chunk], embedder: Embedder
) -> None:
    index = PayloadVectorIndex(clock=later_clock)
    index.upsert(_vectors(corpus, embedder))
    index.delete("doc-2")
    assert not index.search([1.0] * 16, top_k=10, filters={"doc_id": "doc-2"})
    retained: list[dict[str, Any]] = index.payloads(include_stale=True)
    assert any(item["doc_id"] == "doc-2" and not item["is_live"] for item in retained)
