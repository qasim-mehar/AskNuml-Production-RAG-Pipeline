# ADR 0005 — Dependency batch for the merged lanes

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

The eight lanes requested third-party libraries while building against frozen
core contracts. Lockfile regeneration was parked during the merge wave because
the environment is offline, but each lane declared its own pins in its
distribution's `pyproject.toml`. `uv.lock` and the workspace metadata already
carry these requests; this ADR records the full set as the single authoritative
inventory so the integration pass does not renegotiate versions (L1, L8).

## Decision

Adopt the following dependency set, exactly as declared by the lanes:

| Package | Requested by | Pin |
| --- | --- | --- |
| `httpx` | A (crawler, real fetcher); dev/test transport | `>=0.27` |
| `qdrant-client` | D (indexing) | `>=1.12,<2` |
| `minio` | D (indexing) | `>=7.2,<8` |
| `sqlalchemy` | D (indexing) | `>=2.0,<3` |
| `alembic` | D (indexing); root dev group | `>=1.13,<2` |
| `psycopg[binary]` | D (indexing) | `>=3.2,<4` |
| `google-genai` | E (optional extra `google`) | `>=1.0` |
| `openai` | E (optional extra `openai`) | `>=1.0` |
| `fastapi` | G (API) | `>=0.115` |
| `uvicorn[standard]` | G (API) | `>=0.30` |
| `pydantic` | G (API), F (eval), core | `>=2.9` for core/API, `>=2.0` for eval |
| `pydantic-settings` | G (API), core | `>=2.5` |

`uni-rag-core` continues to depend only on `pydantic>=2.9` and
`pydantic-settings>=2.5`; framework SDKs stay optional extras imported lazily
inside Lane E's adapters (L15). Docling remains **unpinned and undeclared**:
the reported candidate is `2.152.0`, but no wheel is resolvable offline, and
Lane B's `pyproject.toml` keeps a documented comment plus fixture fallbacks
instead of a requirement that would break `uv sync` (L1, L4). MinerU is parked
in `docs/PARKING_LOT.md`.

## Alternatives

- **Add Docling at the candidate pin now** — rejected: `uv sync` fails offline,
  which breaks every gate before the integration pass can start.
- **Loosen the lane pins to bare names** — rejected: the upper bounds on the D
  stack and the lower bounds on `pydantic`/`httpx` are deliberate compatibility
  guarantees recorded by the owning lanes.

## Consequences

- One recorded inventory; no lane may renegotiate a pin without its own ADR.
- Lockfile regeneration stays parked until a network-enabled host is available;
  `uv sync --all-packages` must remain green on the current lock.
- Optional extras stay opt-in and never run in CI (L4, ADR 0002).
