# ADR 0009 — Local-only feedback contract and API-local SSE envelopes

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

ADR 0004 promoted Lane H's feedback capture but explicitly granted "local UI
state only — no new auth or persistence scope". Lane H nevertheless ships a
mocked `POST /api/feedback` and a Lane G endpoint expectation, so the UI can
honestly report success or failure. Lane G raised the question and self-answered
that no storage scope is appropriate yet; Lane F parked real feedback-to-golden
ingestion. Meanwhile the streaming surfaces (`TokenEvent`, `CitationsEvent`)
live in `apps/api` and Lane H mirrors them in TypeScript. Both need a settled
contract before the integration pass.

## Decision

Define `POST /api/v1/feedback` as a **local-only transport contract**:

- Request body is a strict JSON object:
  `{ "answer_id": str, "sentiment": "positive" | "negative",
     "reason"?: str, "query_id"?: str }`. Unknown fields are rejected with the
  existing typed `422` `ErrorBody`.
- Response is `202 Accepted`. The body **echoes the validated payload**; the
  response carries the active trace id in both `x-request-id` (Lane H's client)
  and the configured `api.trace_header` (default `X-Trace-Id`, from the trace
  middleware). The route is idempotent from the caller's point of view and
  validates before echoing.
- The handler **persists nothing**: no database write, no object-store write,
  no golden-set ingestion. `answer_id` is echoed as supplied, not looked up.
- It emits one structured log line (`feedback.received`) carrying `answer_id`,
  `sentiment`, whether `reason`/`query_id` were present, and the trace id
  from the logging context (L10). No `print`, no swallowed exception (L11).

Lane G implements this route in its G2 milestone. Lane H aligns its mocked client with the
versioned path and `202` response at migration; its current
`apps/web/CONTRACTS.md` line (`POST /api/feedback`, `204`) is superseded by
this ADR.

**SSE envelopes stay API-local.** `TokenEvent` and `CitationsEvent` are
transport framing for the stream, not domain contracts; they remain in
`uni_rag_api.schemas` with Lane H's TypeScript mirrors. No core port or schema
is promoted for them (L3).

## Alternatives

- **Persist feedback now** — rejected: storage and golden-set ingestion are
  parked for F; granting them here would contradict ADR 0004 and L1.
- **Promote the SSE envelopes to core** — rejected: they carry no domain
  meaning and would put transport detail behind a frozen port (L3).

## Consequences

- The UI has a real, testable feedback endpoint that returns an honest success
  signal without implying feedback was stored.
- Trace ids propagate through feedback the same way as queries (L10).
- F's future feedback-to-golden milestone starts from a logged event stream;
  the storage decision is still an ADR away and stays in
  `docs/PARKING_LOT.md`.
