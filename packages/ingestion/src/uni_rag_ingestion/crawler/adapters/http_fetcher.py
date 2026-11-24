"""Real synchronous HTTP fetcher (ADR-0003).

The ``Fetcher`` port stays frozen: ``fetch(url) -> FetchResult``. Conditional
headers are supplied by an injected provider so the port signature is intact;
response headers are retained at the adapter boundary because ``FetchResult``
has no header field. See the CONTRACT-CHANGE note in the handoff (L3, L12).
"""

from collections.abc import Callable, Mapping
from typing import Final

import httpx

from uni_rag_core.errors import FetchError
from uni_rag_core.schemas import FetchResult

_DEFAULT_ACCEPT: Final[str] = "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8"


class HttpFetcher:
    """Fetch URLs with a polite user agent and optional conditional headers."""

    def __init__(
        self,
        client: httpx.Client,
        *,
        user_agent: str,
        conditional_headers_for: Callable[[str], Mapping[str, str]] | None = None,
    ) -> None:
        self._client = client
        self._user_agent = user_agent
        self._conditional_headers_for = conditional_headers_for
        self._last_request_headers: dict[str, str] = {}
        self._last_response_headers: dict[str, str] = {}

    def fetch(self, url: str) -> FetchResult:
        """Fetch ``url`` synchronously, mapping HTTP failures to ``FetchError``."""
        headers: dict[str, str] = {"User-Agent": self._user_agent, "Accept": _DEFAULT_ACCEPT}
        if self._conditional_headers_for is not None:
            headers.update(dict(self._conditional_headers_for(url)))
        self._last_request_headers = dict(headers)

        try:
            response = self._client.get(url, headers=headers, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise FetchError(
                f"HTTP fetch failed for {url}", context={"url": url, "error": str(exc)}
            ) from exc

        self._last_response_headers = dict(response.headers)
        if response.status_code >= 400:
            raise FetchError(
                f"HTTP {response.status_code} for {url}",
                context={"url": url, "status_code": response.status_code},
            )
        return FetchResult(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            body=response.content,
        )

    @property
    def last_request_headers(self) -> dict[str, str]:
        """Headers sent with the most recent request (for observability/tests)."""
        return dict(self._last_request_headers)

    @property
    def last_response_headers(self) -> dict[str, str]:
        """Raw response headers of the most recent fetch (no port field exists)."""
        return dict(self._last_response_headers)
