# ADR 0002 — Real provider adapters for Lane E

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

Foundation stage ships only deterministic fakes, so no real accuracy number can be
measured for `LLM` or `Embedder`. Promoting real providers is a scope change under
`docs/PARKING_LOT.md` and therefore needs an ADR before Lane E relies on it (L1).
Live calls must never make CI non-deterministic (L4), and framework types must
not leak out of their adapter or across a port (L3, L15).

## Decision

Promote real `google-genai` `LLM`/`Embedder` adapters plus one second provider
adapter (`openai` or a local model) for Lane E, implemented behind the frozen
ports with no new core port or schema. Live calls are opt-in via settings and
never run in CI; deterministic fakes remain the default and every adapter passes
the shared contract test in `tests/contracts/` (L17). The opt-in setting does not
exist yet: Lane 0 must add it in a separate `CONTRACT-CHANGE` PR with its own ADR
before any live call is wired, so until then Lane E builds and tests adapters
against fakes only. All framework imports stay inside
`packages/retrieval/src/uni_rag_retrieval/adapters/` (or `graph/`), enforced by
the `.importlinter` contract (L15).

## Consequences

Lane E can now prove provider quality with measured eval rows; provider
comparison is an eval run (Lane F), not a graph branch or a new law. CI stays
hermetic because fakes remain the default and live credentials are opt-in. Any
new setting, port or schema still requires a `CONTRACT-CHANGE` PR with its own
ADR, so this ADR grants provider-adapter scope only and does not itself change
core settings.
