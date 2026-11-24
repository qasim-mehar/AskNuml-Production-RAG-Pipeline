"""The fakes pass the same contracts that lane adapters must pass."""

from tests.contracts.port_contracts import (
    assert_clock_contract,
    assert_embedder_contract,
    assert_fetcher_contract,
    assert_fetcher_v2_contract,
    assert_llm_contract,
    assert_object_store_contract,
    assert_reranker_contract,
    assert_vector_payload_roundtrip_contract,
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
    SystemClock,
)


def test_embedder_fake_contract() -> None:
    assert_embedder_contract(FakeEmbedder())


def test_reranker_fake_contract() -> None:
    assert_reranker_contract(FakeReranker())


def test_vector_store_fake_contract() -> None:
    assert_vector_store_contract(FakeVectorStore())


def test_vector_store_fake_payload_roundtrip_contract() -> None:
    assert_vector_payload_roundtrip_contract(FakeVectorStore())


def test_llm_fake_contract() -> None:
    assert_llm_contract(FakeLLM())


def test_object_store_fake_contract() -> None:
    assert_object_store_contract(FakeObjectStore())


def test_fetcher_fake_contract() -> None:
    assert_fetcher_contract(FakeFetcher({fetch_result().url: fetch_result()}))


def test_fetcher_fake_v2_contract() -> None:
    assert_fetcher_v2_contract(FakeFetcher({fetch_result().url: fetch_result()}))


def test_fetcher_fake_redirect_chain_is_deterministic() -> None:
    registered = fetch_result().model_copy(update={"final_url": "https://example.edu/final"})
    fetcher = FakeFetcher({registered.url: registered})
    first = fetcher.fetch(registered.url)
    second = fetcher.fetch(registered.url)
    assert first.redirect_chain == second.redirect_chain
    assert [hop.status_code for hop in first.redirect_chain] == [302, 200]
    assert [hop.url for hop in first.redirect_chain] == [registered.url, registered.final_url]


def test_fetcher_fake_records_request_headers() -> None:
    fetcher = FakeFetcher({fetch_result().url: fetch_result()})
    fetcher.fetch(fetch_result().url, request_headers={"If-None-Match": '"v1"'})
    assert dict(fetcher.last_request_headers) == {"If-None-Match": '"v1"'}


def test_clock_fake_contract() -> None:
    assert_clock_contract(FakeClock())


def test_system_clock_contract() -> None:
    assert_clock_contract(SystemClock())


def test_system_clock_moves_forward_without_replacing_the_fake() -> None:
    clock = SystemClock()
    first = clock.now()
    second = clock.now()
    assert second >= first
    assert FakeClock(first).now() == first
    assert FakeClock(first).now() == FakeClock(first).now()
