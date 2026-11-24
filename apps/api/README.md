# uni-rag-api

FastAPI service for uni-rag, backed by deterministic fakes (L3, L4). No live
model or network call is made by this app or its tests.

## Routes

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health/live` | Liveness (no dependency checks) |
| GET | `/health/ready` | Readiness via the injected health probe |
| POST | `/api/v1/query` | Return a cited `Answer`, or an explicit abstention |
| POST | `/api/v1/query/stream` | SSE tokens, ending with a `citations` event carrying the `Answer` |

Every response carries `X-Trace-Id`; logs are structured JSON with the same id.
An optional `X-API-Key` stub and an in-memory token bucket are settings-driven.
The committed `openapi.json` is the contract for the web lane.

## Tooling

- `uv run pytest apps/api/tests` — lane tests (fixtures first).
- `uv run python apps/api/scripts/generate_openapi.py` — regenerate the artifact.
- `uv run python apps/api/scripts/benchmark.py --requests 200` — p95 against the
  **fake backend only**, in-process, labelled as such (L1); not production capacity.

Owned by the **API lane**; depends on `uni-rag-core` and never on another app.
