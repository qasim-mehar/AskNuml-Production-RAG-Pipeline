"""HTTP fetcher port (L3)."""

from typing import Protocol, runtime_checkable

from uni_rag_core.schemas import FetchResult


@runtime_checkable
class Fetcher(Protocol):
    """Fetches source URLs without leaking an HTTP client to domain code."""

    def fetch(self, url: str) -> FetchResult:
        """Fetch ``url`` and return status, final URL, content type and body."""
        ...
