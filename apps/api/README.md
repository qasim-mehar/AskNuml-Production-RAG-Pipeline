# uni-rag-api

FastAPI service for uni-rag. Fakes are the default backend; the real Lane E
pipeline is composed behind the folded core settings flag (L2, L3, L8). No live
model or network call is made by this app's tests.

## Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health/live` | Liveness (no dependency checks) |
| GET | `/health/ready` | Readiness via the injected health probe |
| POST | `/api/v1/query` | Return a cited `Answer`, or an explicit abstention |
| POST | `/api/v1/query/stream` | SSE tokens, ending with a `citations` event carrying the `Answer` |
| POST | `/api/v1/feedback` | Validate, log and echo feedback (`202`); persists nothing (ADR 0009) |
| GET | `/api/images/{ref_id}` | Stream stored page-image bytes from the ObjectStore port |

Every response carries `x-request-id` and `X-Trace-Id`; logs are structured JSON
with the same id. An optional `X-API-Key` stub and an in-memory token bucket are
settings-driven. The committed `openapi.json` is the contract for Lane H.

## Backends

`Settings.providers.live_enabled` derives the backend: off (the CI default)
keeps the deterministic fake corpus; on selects Lane E's public `RetrievalPipeline`
with vector/object-store adapters from settings. `create_app(..., backend=...)`
can override the flag; `pipeline_ports` and `object_store` allow a deterministic
all-fake "real" composition for tests (L4). Live LLM/Embedder adapters must be
injected — the API never imports a provider SDK (L3).

## Tooling

- `uv run pytest apps/api/tests` — lane tests (fixtures first).
- `uv run python apps/api/scripts/generate_openapi.py` — regenerate the artifact.
- `uv run python apps/api/scripts/benchmark.py --requests 200 --backend fake|real`
  — in-process, single-connection latency labelled by backend (L1); not
  production capacity.

Owned by the **API lane**; depends on `uni-rag-core`, Lane E's public service and
Lane D's storage adapters behind ports — never on another app.
