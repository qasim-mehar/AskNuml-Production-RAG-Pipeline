"""Sparse collection lifecycle: hard deletion must never masquerade as stale."""

from __future__ import annotations

from uni_rag_core import Chunk
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore

INDICES = [0, 1, 2]
VALUES = [0.9, 0.4, 0.1]


def _search(store: QdrantVectorStore) -> list[str]:
    return [hit.chunk_id for hit in store.search_sparse(indices=INDICES, values=VALUES, top_k=10)]


def test_sparse_points_are_soft_deleted_on_document_delete(
    qdrant_local: QdrantVectorStore, base_chunk: Chunk
) -> None:
    qdrant_local.upsert_sparse(base_chunk, indices=INDICES, values=VALUES)
    assert _search(qdrant_local) == ["chunk-1"]

    qdrant_local.delete(base_chunk.doc_id)
    assert _search(qdrant_local) == []

    points, _ = qdrant_local._client.scroll(
        collection_name="chunks_sparse", scroll_filter=None, with_payload=True, with_vectors=False
    )
    retained = [point for point in points if point.payload is not None]
    assert len(retained) == 1
    assert retained[0].payload["is_live"] is False
    assert retained[0].payload["deleted_at"] is not None


def test_sparse_supersede_keeps_only_the_new_version_live(
    qdrant_local: QdrantVectorStore, base_chunk: Chunk
) -> None:
    qdrant_local.upsert_sparse(base_chunk, indices=INDICES, values=VALUES)
    changed = base_chunk.model_copy(update={"content_hash": "sparse-v2", "version": "2"})
    qdrant_local.upsert_sparse(changed, indices=INDICES, values=VALUES)

    assert len(_search(qdrant_local)) == 1
    points, _ = qdrant_local._client.scroll(
        collection_name="chunks_sparse", scroll_filter=None, with_payload=True, with_vectors=False
    )
    states = sorted(bool(point.payload and point.payload["is_live"]) for point in points)
    assert states == [False, True]
