"""The fakes pass the same contracts that lane adapters must pass."""

from tests.contracts.port_contracts import (
    assert_clock_contract,
    assert_embedder_contract,
    assert_fetcher_contract,
    assert_llm_contract,
    assert_object_store_contract,
    assert_reranker_contract,
    assert_vector_store_contract,
)
from tests.factories import fetch_result
from uni_rag_core import (
    FakeClock,
    FakeEmbedder,
    FakeFetcher,
    FakeLLM,
    FakeObjectStore,
    FakeReranker,
    FakeVectorStore,
)


def test_embedder_fake_contract() -> None:
    assert_embedder_contract(FakeEmbedder())


def test_reranker_fake_contract() -> None:
    assert_reranker_contract(FakeReranker())


def test_vector_store_fake_contract() -> None:
    assert_vector_store_contract(FakeVectorStore())


def test_llm_fake_contract() -> None:
    assert_llm_contract(FakeLLM())


def test_object_store_fake_contract() -> None:
    assert_object_store_contract(FakeObjectStore())


def test_fetcher_fake_contract() -> None:
    assert_fetcher_contract(FakeFetcher({fetch_result().url: fetch_result()}))


def test_clock_fake_contract() -> None:
    assert_clock_contract(FakeClock())
