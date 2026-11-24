"""Every fake satisfies its port at runtime (L3, L4)."""

import pytest

from tests.factories import chunk, fetch_result
from uni_rag_core import (
    LLM,
    Clock,
    Embedder,
    FakeClock,
    FakeEmbedder,
    FakeFetcher,
    FakeLLM,
    FakeObjectStore,
    FakeReranker,
    FakeVectorStore,
    Fetcher,
    ObjectStore,
    Reranker,
    VectorStore,
)

PORTS_AND_FAKES = [
    (Clock, FakeClock()),
    (Embedder, FakeEmbedder()),
    (Fetcher, FakeFetcher()),
    (LLM, FakeLLM()),
    (ObjectStore, FakeObjectStore()),
    (Reranker, FakeReranker()),
    (VectorStore, FakeVectorStore()),
]


@pytest.mark.parametrize(
    ("port", "fake"),
    PORTS_AND_FAKES,
    ids=lambda value: getattr(value, "__name__", type(value).__name__),
)
def test_fake_satisfies_port(port: type, fake: object) -> None:
    assert isinstance(fake, port)


def test_fake_embedder_is_deterministic() -> None:
    embedder = FakeEmbedder(dimension=16)
    first = embedder.embed(["alpha", "beta"])
    second = embedder.embed(["alpha", "beta"])
    assert first == second
    assert all(len(vector) == 16 for vector in first)
    assert first[0] != first[1]


def test_fake_vector_store_ranks_and_filters() -> None:
    store = FakeVectorStore()
    target = chunk()
    other = chunk().model_copy(update={"chunk_id": "chunk-2", "doc_id": "doc-2"})
    store.upsert([(target, [1.0, 0.0]), (other, [0.0, 1.0])])
    hits = store.search([1.0, 0.0], top_k=2)
    assert [hit.chunk_id for hit in hits] == ["chunk-1", "chunk-2"]
    filtered = store.search([1.0, 0.0], top_k=2, filters={"doc_id": "doc-2"})
    assert [hit.chunk_id for hit in filtered] == ["chunk-2"]
    store.delete("doc-2")
    assert store.search([1.0, 0.0], top_k=2)[0].chunk_id == "chunk-1"


def test_fake_object_store_roundtrip() -> None:
    store = FakeObjectStore()
    key = store.put("page.png", b"png-bytes", content_type="image/png")
    assert store.get(key) == b"png-bytes"
    assert store.content_type_of(key) == "image/png"
    store.delete(key)
    assert key not in store._objects  # noqa: SLF001 - fake-specific inspection in test


def test_fake_fetcher_raises_for_unknown_url() -> None:
    from uni_rag_core import FetchError

    fetcher = FakeFetcher({"https://example.edu/ok": fetch_result()})
    assert fetcher.fetch("https://example.edu/ok").status_code == 200
    with pytest.raises(FetchError, match="no fake response"):
        fetcher.fetch("https://example.edu/missing")
