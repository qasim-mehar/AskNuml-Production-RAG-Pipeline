# @uni-rag/web

Next.js App Router frontend for uni-rag, written in strict TypeScript.

Owned by the **web lane**. Routes: `/` (health), `/chat` (cited streaming chat),
`/papers` (past-paper finder). Urdu is right-to-left; Roman Urdu is Latin-script.

## Layers

- `lib/` — pure formatters, strict Zod mirrors of the frozen core schemas,
  the API client, and the deterministic fetch mock router with fixtures.
- `components/` — presentational; no fetching.
- `features/` — composition and hooks (`useChat`, `usePapers`).

No component fetches. API responses are validated at the edge; a schema mismatch
raises a typed `ApiError` and renders an alert, never a partial answer.

## Validation library

`zod` (runtime dependency) mirrors `packages/core/src/uni_rag_core/schemas/`.
`src/lib/api/mocks/core-emitted.json` is generated from the Pydantic models by
`uv run python apps/web/scripts/generate_contract_fixture.py` (run from the repo
root) and is the contract-fidelity fixture for `schemas.test.ts`. Lane G endpoint
expectations and CONTRACT-CHANGE items are recorded in `CONTRACTS.md`.

## Tests

`pnpm test` uses Vitest + jsdom + Testing Library with a deterministic fetch
router (an MSW-equivalent; MSW's build script is not approved by the workspace-root
pnpm allowlist, which is Lane 0-owned). Streaming is driven by fake timers; axe-core
checks zero critical violations on both pages. No test touches the network.

## Local Lighthouse

Run `pnpm build && pnpm start`, then `npx lighthouse http://localhost:3000/chat`
and `/papers`. Scoring is local-only and is reported in the lane handoff; CI does
not assert scores (L1).
