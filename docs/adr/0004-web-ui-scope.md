# ADR 0004 — Student-facing web UI for Lane H

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

Lane H was limited to a health page while `docs/PARKING_LOT.md` parked "UI beyond
a health page". The product cannot be demonstrated to students without a cited
answer experience, and the API's OpenAPI document does not exist until Lane G
lands. Promoting the UI is a scope change that needs an ADR before Lane H relies
on it (L1), and the UI must not redefine the frozen `Query`/`Answer` schemas
(L3) or drop language parity (L7).

## Decision

Promote a student-facing web UI for Lane H: cited chat with streaming, a
past-paper finder and a feedback capture, built against the frozen `Query` and
`Answer` schemas mirrored in TypeScript and a mocked API client until Lane G's
OpenAPI lands. No core schema, port or setting changes; no live backend is
required for tests, and citations and past-paper page images render from the
schemas' existing fields (L5).

## Consequences

Lane H is unblocked and can ship UI while Lane G is still in flight; swapping the
mock for the real client later does not change components. Because the schemas
are frozen, any contract change needs a `CONTRACT-CHANGE` PR with its own ADR.
RTL Urdu and Roman Urdu remain first-class in the UI (L7), and feedback is local
UI state only — no new auth or persistence scope is granted.
