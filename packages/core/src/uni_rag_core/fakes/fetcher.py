"""Deterministic in-memory Fetcher fake."""

import hashlib
from collections.abc import Mapping

from uni_rag_core.errors import FetchError
from uni_rag_core.schemas import FetchResult, RedirectHop


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
        self._last_request_headers: dict[str, str] = {}

    @property
    def last_request_headers(self) -> Mapping[str, str]:
        """Return the request headers supplied to the most recent fetch."""
        return dict(self._last_request_headers)

    def register(self, url: str, response: FetchResult) -> None:
        """Register (or replace) a URL response."""
        self._responses[url] = response

    def fetch(self, url: str, *, request_headers: Mapping[str, str] | None = None) -> FetchResult:
        """Return the registered response with deterministic synthetic metadata."""
        response = self._responses.get(url, self._default)
        if response is None:
            msg = f"no fake response registered for {url}"
            raise FetchError(msg, context={"url": url})

        self._last_request_headers = dict(request_headers or {})
        headers = dict(response.headers)
        headers.setdefault("etag", self._etag_for(url))
        headers.setdefault("content-type", response.content_type)

        update: dict[str, object] = {
            "headers": headers,
            "redirect_chain": self._chain_for(url, response),
        }
        response_etag = next(
            (value for key, value in headers.items() if key.lower() == "etag"), None
        )
        request = {key.lower(): value for key, value in self._last_request_headers.items()}
        if response_etag is not None and request.get("if-none-match") == response_etag:
            update["status_code"] = 304
            update["body"] = b""
        return response.model_copy(update=update)

    @staticmethod
    def _etag_for(url: str) -> str:
        """Derive a stable validator from the requested URL (L4)."""
        return f'"{hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]}"'

    @staticmethod
    def _chain_for(url: str, response: FetchResult) -> tuple[RedirectHop, ...]:
        """Return a registered chain, or a deterministic one when URLs differ."""
        if response.redirect_chain:
            return response.redirect_chain
        if url == response.final_url:
            return ()
        return (
            RedirectHop(url=url, status_code=302),
            RedirectHop(url=response.final_url, status_code=response.status_code),
        )
