"""Real fetcher specs: shared contract against a local server, no live web."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import cast

import httpx
import pytest

from tests.contracts.port_contracts import assert_fetcher_contract
from uni_rag_core import FetchError, FetchResult
from uni_rag_ingestion.crawler.adapters import HttpFetcher
from uni_rag_ingestion.crawler.domain import ConditionalStore, Validators


@dataclass
class _Route:
    status: int
    body: bytes
    content_type: str = "text/html; charset=utf-8"
    headers: dict[str, str] = field(default_factory=dict)


class _Server(ThreadingHTTPServer):
    routes: dict[str, _Route]
    seen: list[dict[str, str]]


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        server = cast(_Server, self.server)
        server.seen.append({key.lower(): value for key, value in self.headers.items()})
        path = self.path.split("?", 1)[0]

        if path == "/not-modified" and self.headers.get("If-None-Match") == '"v1"':
            self.send_response(304)
            self.send_header("ETag", '"v1"')
            self.end_headers()
            return

        route = server.routes.get(path)
        if route is None:
            self.send_error(404)
            return

        self.send_response(route.status)
        self.send_header("Content-Type", route.content_type)
        self.send_header("Content-Length", str(len(route.body)))
        for key, value in route.headers.items():
            self.send_header(key, value)
        self.end_headers()
        if route.status != 304:
            self.wfile.write(route.body)

    def log_message(self, fmt: str, *args: object) -> None:
        """Silence the stdlib stdout logger; application logs are structured (L10)."""
        return


class _LocalOnlyTransport(httpx.BaseTransport):
    """Fail closed for any host other than the local test server (L4, L12)."""

    def __init__(self, inner: httpx.BaseTransport, host: str) -> None:
        self._inner = inner
        self._host = host

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host != self._host:
            raise httpx.ConnectError(f"blocked non-local host {request.url.host}", request=request)
        return self._inner.handle_request(request)

    def close(self) -> None:
        """Close the wrapped transport with the client."""
        self._inner.close()


@pytest.fixture
def local_server() -> Iterator[tuple[str, _Server]]:
    """Serve checked-in behaviour from an ephemeral loopback port."""
    server = _Server(("127.0.0.1", 0), _Handler)
    server.routes = {
        "/ok": _Route(200, b"<html><body>ok</body></html>", headers={"ETag": '"v1"'}),
        "/redirect": _Route(302, b"", headers={"Location": "/ok"}),
        "/missing": _Route(404, b""),
    }
    server.seen = []
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)


@pytest.fixture
def client(local_server: tuple[str, _Server]) -> Iterator[httpx.Client]:
    """An httpx client that can reach only the local test server."""
    with httpx.Client(
        timeout=5.0,
        transport=_LocalOnlyTransport(httpx.HTTPTransport(), "127.0.0.1"),
    ) as value:
        yield value


def test_fetcher_adapter_passes_shared_contract(
    client: httpx.Client, local_server: tuple[str, _Server], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real adapter passes tests/contracts against the local server."""
    base, _ = local_server
    monkeypatch.setattr(
        "tests.contracts.port_contracts.fetch_result",
        lambda: FetchResult(
            url=f"{base}/ok",
            final_url=f"{base}/ok",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=b"<html><body>ok</body></html>",
        ),
    )
    assert_fetcher_contract(HttpFetcher(client, user_agent="uni-rag-crawler/0.1"))


def test_fetch_result_carries_status_url_type_and_body(
    client: httpx.Client, local_server: tuple[str, _Server]
) -> None:
    base, _ = local_server
    result = HttpFetcher(client, user_agent="uni-rag-crawler/0.1").fetch(f"{base}/ok")
    assert result.status_code == 200
    assert result.final_url == f"{base}/ok"
    assert "text/html" in result.content_type
    assert b"ok" in result.body


def test_redirect_is_followed_and_final_url_is_recorded(
    client: httpx.Client, local_server: tuple[str, _Server]
) -> None:
    base, _ = local_server
    result = HttpFetcher(client, user_agent="uni-rag-crawler/0.1").fetch(f"{base}/redirect")
    assert result.status_code == 200
    assert result.final_url == f"{base}/ok"
    assert b"ok" in result.body


def test_http_404_is_mapped_to_fetch_error(
    client: httpx.Client, local_server: tuple[str, _Server]
) -> None:
    base, _ = local_server
    with pytest.raises(FetchError):
        HttpFetcher(client, user_agent="uni-rag-crawler/0.1").fetch(f"{base}/missing")


def test_conditional_headers_are_sent_and_304_has_empty_body(
    client: httpx.Client, local_server: tuple[str, _Server]
) -> None:
    base, server = local_server
    store = ConditionalStore()
    store.record(f"{base}/not-modified", Validators(etag='"v1"'))
    fetcher = HttpFetcher(
        client,
        user_agent="uni-rag-crawler/0.1",
        conditional_headers_for=store.headers_for,
    )

    result = fetcher.fetch(f"{base}/not-modified")
    assert result.status_code == 304
    assert result.body == b""
    assert server.seen[-1]["if-none-match"] == '"v1"'
    assert fetcher.last_request_headers["User-Agent"] == "uni-rag-crawler/0.1"

    store.record_from_headers(result.url, fetcher.last_response_headers)
    assert store.get(result.url) == Validators(etag='"v1"')
