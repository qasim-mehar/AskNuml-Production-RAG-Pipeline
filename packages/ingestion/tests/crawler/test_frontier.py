"""Frontier specs: BFS order, depth cap and canonical dedup."""

import pytest

from uni_rag_core import ValidationError
from uni_rag_ingestion.crawler.domain import Frontier, canonicalize_url


def test_canonicalize_url_drops_fragment_default_port_and_sorts_query() -> None:
    result = canonicalize_url("https://Example.edu:443/courses/list/?b=2&a=1#section")
    assert result == "https://example.edu/courses/list?a=1&b=2"


def test_canonicalize_url_rejects_non_http_url() -> None:
    with pytest.raises(ValidationError):
        canonicalize_url("ftp://example.edu/file.txt")


def test_frontier_visits_breadth_first_and_honours_depth_cap() -> None:
    frontier = Frontier(["https://example.edu/"], max_depth=1)
    assert frontier.add("https://example.edu/a", 1)
    assert not frontier.add("https://example.edu/deep", 2)

    root = frontier.pop()
    assert root is not None and root.url == "https://example.edu/"

    assert frontier.add("https://example.edu/b", 1)
    first = frontier.pop()
    second = frontier.pop()
    assert first is not None and first.url == "https://example.edu/a"
    assert second is not None and second.url == "https://example.edu/b"
    assert frontier.pop() is None


def test_frontier_dedupes_canonical_equivalents() -> None:
    frontier = Frontier(["https://example.edu/course"], max_depth=2)
    assert not frontier.add("https://EXAMPLE.edu:443/course/#top", 1)
    assert len(frontier.seen) == 1
