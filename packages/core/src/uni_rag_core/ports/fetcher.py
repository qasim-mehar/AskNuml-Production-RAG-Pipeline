"""HTTP fetcher port (L3)."""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from uni_rag_core.schemas import FetchResult


@runtime_checkable
class Fetcher(Protocol):
    """Fetches source URLs without leaking an HTTP client to domain code."""

    def fetch(self, url: str, *, request_headers: Mapping[str, str] | None = None) -> FetchResult:
        """Fetch ``url`` and return status, final URL, headers, hops and body.

        ``request_headers`` lets a caller round-trip conditional-request
        validators (ADR 0006). It is optional: an adapter that ignores it still
        satisfies the port, but only v2 adapters can assert the header round-trip
        in the shared contract suite.
        """
        ...
