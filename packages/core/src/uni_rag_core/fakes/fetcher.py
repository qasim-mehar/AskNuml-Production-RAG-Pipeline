"""Deterministic in-memory Fetcher fake."""

from collections.abc import Mapping

from uni_rag_core.errors import FetchError
from uni_rag_core.schemas import FetchResult


class FakeFetcher:
    """Serves pre-registered responses; unknown URLs raise ``FetchError``."""

    def __init__(
        self,
        responses: Mapping[str, FetchResult] | None = None,
        *,
        default: FetchResult | None = None,
    ) -> None:
        self._responses = dict(responses or {})
        self._default = default

    def register(self, url: str, response: FetchResult) -> None:
        """Register (or replace) a URL response."""
        self._responses[url] = response

    def fetch(self, url: str) -> FetchResult:
        """Return the registered response for ``url``."""
        response = self._responses.get(url, self._default)
        if response is None:
            msg = f"no fake response registered for {url}"
            raise FetchError(msg, context={"url": url})
        return response
