"""Conditional-store specs: validators key the If-* headers per URL."""

from uni_rag_ingestion.crawler.domain import ConditionalStore, Validators


def test_unknown_url_sends_no_conditional_headers() -> None:
    store = ConditionalStore()
    assert store.headers_for("https://example.edu/a") == {}
    assert store.get("https://example.edu/a") is None


def test_recorded_validators_produce_conditional_headers() -> None:
    store = ConditionalStore()
    store.record("https://example.edu/a", Validators(etag='"v7"', last_modified="Tue, 24 Nov 2026"))
    assert store.headers_for("https://example.edu/a") == {
        "If-None-Match": '"v7"',
        "If-Modified-Since": "Tue, 24 Nov 2026",
    }
    assert store.headers_for("https://example.edu/b") == {}


def test_record_from_headers_is_case_insensitive_and_skips_empty() -> None:
    store = ConditionalStore()
    store.record_from_headers("https://example.edu/a", {"ETag": '"v1"'})
    store.record_from_headers("https://example.edu/b", {"content-type": "text/html"})
    assert store.get("https://example.edu/a") == Validators(etag='"v1"')
    assert store.get("https://example.edu/b") is None


def test_forget_clears_validators() -> None:
    store = ConditionalStore()
    store.record("https://example.edu/a", Validators(etag='"v1"'))
    store.forget("https://example.edu/a")
    assert store.headers_for("https://example.edu/a") == {}
