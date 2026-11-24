# ADR 0006 — Fetcher contract v2 (headers and redirect chain)

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

Lane A built the polite crawler against the frozen `Fetcher.fetch(url)` port.
That port cannot round-trip conditional-request validators (`If-None-Match`,
`If-Modified-Since`) and carries neither response headers nor redirect hops, so
per-hop robots/rate gating of redirects is impossible through the port. Lane A
honestly worked around it with a `conditional_headers_for` callback plus
out-of-band `last_request_headers` / `last_response_headers` accessors instead
of patching core (L3, L14). This is contract friction, not a lane bug.

## Decision

Extend the fetcher contract backwards-compatibly:

- `FetchResult` gains `headers: Mapping[str, str]` and
  `redirect_chain: tuple[RedirectHop, ...]`, where `RedirectHop` carries `url`
  and the integer `status_code` that produced the hop. Both default to empty,
  so existing constructions keep compiling.
- `Fetcher.fetch(url, *, request_headers: Mapping[str, str] | None = None)` gains
  an optional keyword-only argument. Positional and one-argument calls are
  unchanged.
- `FakeFetcher` accepts `request_headers`, exposes `last_request_headers`, and
  returns deterministic synthetic metadata: a stable URL-derived `etag`, the
  content type, and a two-hop chain when `url != final_url`. A matching
  `If-None-Match` yields 304 with an empty body, so validators genuinely
  round-trip in unit tests.
- `tests/contracts/port_contracts.py` asserts the new fields for every adapter
  and provides `assert_fetcher_v2_contract` for the request-header round-trip.

The v1 helper remains the gate for lane adapters until they migrate their own
shims; only the fakes are required to pass the v2 helper in this wave. The new
keyword is optional at the port level, so a v1 adapter (Lane A's current
`HttpFetcher.fetch(url)`) still satisfies `Fetcher` and must keep being called
with one argument. Integration callers must not pass `request_headers` to an
adapter until that lane accepts it; `assert_fetcher_v2_contract` first checks
the method signature so misuse fails with a clear contract message rather than
a `TypeError`. Lane A's migration to accept-and-use the kwarg is a handoff item.

## Alternatives

- **Leave the port frozen and keep the callback shim** — rejected: validators
  and redirect hops would stay out-of-band, so no other lane or the integration
  pass can use them through the port (L3).
- **Make `request_headers` required / fields non-defaulted** — rejected: it
  would break every merged lane call site (L14).

## Consequences

- Lane A can fold `CrawlerConfig`'s conditional store into
  `request_headers` / `result.headers` and gate each redirect hop; its shim
  retires in its next milestone.
- Fakes remain deterministic (L4); no adapter or lane code changes here.
- Every existing fetcher test stays green, which is the backwards-compatibility
  proof for the merged crawler.
