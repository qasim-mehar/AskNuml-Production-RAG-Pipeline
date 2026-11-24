# ADR 0008 — Settings consolidation, live-provider flag, SystemClock and py.typed

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

L8 requires exactly one typed settings module, but three lanes were forced to
declare configuration outside it: G added `ApiSettings` with `UNI_RAG_API_`
keys, A added a domain-local `CrawlerConfig`, and E needed the live-provider
opt-in promised by ADR 0002. D's production path had no real clock in core and
fell back to the test fake. Downstream strict mypy also needed per-file
suppressions because the core wheel shipped no `py.typed` marker.

## Decision

- Fold G's knobs into a nested `Settings.api: ApiSection`: auth enforcement,
  rate-limit capacity/refill/exempt paths, `max_top_k`, trace header and a
  `trace_header_enabled` switch. G deletes its local module at migration.
- Fold A's knobs into `Settings.crawler: CrawlerSection`: `seeds`, `max_depth`,
  `requests_per_second`, `user_agent`. A deletes `CrawlerConfig` at migration.
- Add `Settings.providers: ProvidersSection` with `live_enabled: bool = False`
  and `SecretStr` provider keys. The flag defaults off and a validator rejects
  enabling it when `environment` is `ci` or `test`; keys cannot appear in
  `repr` or `model_dump_json`. Fakes remain the default (L4, ADR 0002).
- **Chosen env form:** the nested sections read their **legacy
  `UNI_RAG_<SECTION>_<FIELD>` keys** (e.g. `UNI_RAG_API_RATE_LIMIT_CAPACITY`).
  No deployment must rename a variable. The nested
  `UNI_RAG_<SECTION>__<FIELD>` form is not the documented contract.
- Required infrastructure (`qdrant_url`, `postgres_dsn`, `minio_endpoint`) is
  unchanged and still fails fast. New sections have safe defaults and fail fast
  on invalid values rather than on absence, so existing loads keep working.
- Ship `SystemClock` (datetime-based, framework-free) in core next to
  `FakeClock`. Tests keep injecting `FakeClock`; production injects
  `SystemClock`. D/G retire their local clock module at migration.
- Ship an empty `py.typed` marker inside `uni_rag_core` so strict mypy consumes
  the inline types without per-file suppressions.

## Alternatives

- **Keep the lane-local settings modules** — rejected: violates L8 and leaves
  the integration pass with three sources of truth.
- **Require the new nested values** — rejected: it would break every existing
  settings load and the fail-fast contract for the three required keys.
- **Use only the nested `__` env form** — rejected: it forces an env migration
  on G's deployed configuration for no benefit.

## Consequences

- One settings module again; the API section is nested in `Settings`, not a
  second `BaseSettings` module.
- Lane G folds `ApiSettings`, retires its API-local error subclasses (ADR 0007)
  and its `SystemClock`, and wires the feedback route per ADR 0009 next.
- Lane A folds `CrawlerConfig`; E can opt into live providers with the flag;
  D/G use the core clock.
- Downstream strict mypy no longer needs `py.typed` suppressions.
