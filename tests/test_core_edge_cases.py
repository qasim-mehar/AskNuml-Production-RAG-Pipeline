"""Error branches of the core fakes and settings are pinned."""

import pytest

from tests.factories import chunk, fetch_result
from uni_rag_core import (
    ConfigError,
    FakeClock,
    FakeEmbedder,
    FakeFetcher,
    FakeLLM,
    FakeObjectStore,
    FakeReranker,
    FakeVectorStore,
    FetchError,
    StorageError,
    UniRagError,
    ValidationError,
)
from uni_rag_core.config import Settings


def test_fake_embedder_rejects_non_positive_dimension() -> None:
    with pytest.raises(ValueError, match="dimension"):
        FakeEmbedder(dimension=0)


def test_fake_llm_rejects_empty_prompt() -> None:
    with pytest.raises(ValidationError):
        FakeLLM().complete("   ")


def test_fake_object_store_error_branches() -> None:
    store = FakeObjectStore()
    with pytest.raises(StorageError, match="empty"):
        store.put("", b"data")
    with pytest.raises(StorageError, match="not found"):
        store.get("missing")
    store.delete("missing")


def test_fake_fetcher_uses_default_and_raises_when_absent() -> None:
    default = fetch_result()
    assert FakeFetcher(default=default).fetch("https://any.example").status_code == 200
    with pytest.raises(FetchError):
        FakeFetcher().fetch("https://any.example")


def test_fake_clock_rejects_naive_datetime() -> None:
    from datetime import datetime

    with pytest.raises(ValueError, match="timezone-aware"):
        FakeClock(datetime(2026, 1, 1))


def test_fake_vector_store_handles_empty_and_zero_vectors() -> None:
    store = FakeVectorStore()
    store.upsert([(chunk(), [0.0, 0.0])])
    assert store.search([1.0, 0.0], top_k=0) == []
    assert store.search([0.0, 0.0], top_k=1)[0].score == 0.0
    assert store.search([1.0, 0.0], top_k=1, filters={"unknown": "x"}) == []


def test_fake_reranker_handles_empty_query() -> None:
    scored = FakeReranker().rerank("", [chunk()])
    assert scored[0].score == 0.0


def test_errors_carry_context() -> None:
    error = ConfigError("bad", context={"field": "qdrant_url"})
    assert isinstance(error, UniRagError)
    assert error.context["field"] == "qdrant_url"


def test_settings_reject_invalid_tuning_value() -> None:
    with pytest.raises(ValueError):
        Settings(
            qdrant_url="http://localhost:6333",
            postgres_dsn="postgresql://u:p@localhost/db",
            minio_endpoint="http://localhost:9000",
            embedding_dimension=0,
        )
