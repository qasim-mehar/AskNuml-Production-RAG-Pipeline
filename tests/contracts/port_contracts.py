"""Executable port contracts, parameterised by a concrete adapter.

Every Lane adapter must pass the corresponding ``assert_*_contract`` helper
with its own implementation, not just with the in-memory fake.
"""

from datetime import datetime

from tests.factories import chunk, fetch_result
from uni_rag_core import (
    LLM,
    Clock,
    Embedder,
    Fetcher,
    FetchError,
    ObjectStore,
    Reranker,
    StorageError,
    VectorStore,
)
from uni_rag_core.schemas import Chunk, FetchResult


def assert_embedder_contract(embedder: Embedder) -> None:
    """Embeddings are fixed-width, finite, deterministic and ordered."""
    assert isinstance(embedder, Embedder)
    vectors = embedder.embed(["first", "second"])
    assert len(vectors) == 2
    assert all(len(vector) == embedder.dimension for vector in vectors)
    assert all(-1.0 <= value <= 1.0 for vector in vectors for value in vector)
    assert vectors == embedder.embed(["first", "second"])


def assert_reranker_contract(reranker: Reranker) -> None:
    """Reranking returns descending scores, 1-based ranks and the same chunks."""
    assert isinstance(reranker, Reranker)
    candidates = [
        chunk(),
        chunk().model_copy(update={"chunk_id": "chunk-2", "text": "Unrelated subject here."}),
    ]
    scored = reranker.rerank("midterm grade", candidates)
    assert len(scored) == len(candidates)
    assert [item.rank for item in scored] == list(range(1, len(candidates) + 1))
    assert [item.score for item in scored] == sorted((item.score for item in scored), reverse=True)
    assert {item.chunk.chunk_id for item in scored} == {"chunk-1", "chunk-2"}


def assert_vector_store_contract(store: VectorStore) -> None:
    """VectorStore upserts, filters, deletes and returns ranked hits."""
    assert isinstance(store, VectorStore)
    first: Chunk = chunk()
    second = first.model_copy(update={"chunk_id": "chunk-2", "doc_id": "doc-2"})
    store.upsert([(first, [1.0, 0.0]), (second, [0.0, 1.0])])
    hits = store.search([1.0, 0.0], top_k=2)
    assert len(hits) == 2
    assert hits[0].chunk_id == "chunk-1"
    assert hits[0].score >= hits[1].score
    filtered = store.search([1.0, 0.0], top_k=2, filters={"doc_id": "doc-2"})
    assert [hit.chunk_id for hit in filtered] == ["chunk-2"]
    store.delete("doc-2")
    assert all(hit.chunk_id != "chunk-2" for hit in store.search([1.0, 0.0], top_k=5))


def assert_llm_contract(llm: LLM) -> None:
    """LLM completion is a non-empty string and deterministic for the same input."""
    assert isinstance(llm, LLM)
    first = llm.complete("Summarise the midterm policy.", system="Be concise.")
    assert isinstance(first, str) and first.strip()
    assert first == llm.complete("Summarise the midterm policy.", system="Be concise.")


def assert_object_store_contract(store: ObjectStore) -> None:
    """ObjectStore round-trips bytes and signals missing keys with StorageError."""
    assert isinstance(store, ObjectStore)
    key = store.put("contract/page.bin", b"\x89PNG\r\n\x1a\n", content_type="image/png")
    assert store.get(key) == b"\x89PNG\r\n\x1a\n"
    store.delete(key)
    try:
        store.get(key)
    except StorageError:
        pass
    else:
        raise AssertionError("missing object must raise StorageError")


def assert_fetcher_contract(fetcher: Fetcher) -> None:
    """Fetcher returns a FetchResult and signals unknown URLs with FetchError."""
    assert isinstance(fetcher, Fetcher)
    registered: FetchResult = fetch_result()
    result = fetcher.fetch(registered.url)
    assert result.status_code == 200
    assert result.final_url
    assert isinstance(result.body, bytes)
    try:
        fetcher.fetch("https://example.invalid/unregistered")
    except FetchError:
        pass
    else:
        raise AssertionError("unregistered URL must raise FetchError")


def assert_clock_contract(clock: Clock) -> None:
    """Clock returns a timezone-aware datetime."""
    assert isinstance(clock, Clock)
    now: datetime = clock.now()
    assert now.tzinfo is not None
    assert now.utcoffset() is not None
