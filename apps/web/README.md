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

`zod` (runtime dependency) mirrors the served `apps/api/openapi.json` plus the
frozen core schemas. `uv run python apps/web/scripts/generate_contract_fixture.py`
(run from the repo root) regenerates `mocks/core-emitted.json` from the Pydantic
models and `mocks/openapi-emitted.json` from the artifact's operationIds and
schemas. Both round-trip through the Zod mirrors in `schemas.test.ts`. Lane G
endpoint expectations and CONTRACT-CHANGE items are recorded in `CONTRACTS.md`.

## Tests

`pnpm test` uses Vitest + jsdom + Testing Library with a deterministic fetch
router (an MSW-equivalent; MSW's build script is not approved by the workspace-root
pnpm allowlist, which is Lane 0-owned). Streaming is driven by fake timers; axe-core
checks zero critical violations on both pages. No test touches the network.

## Local Lighthouse — FAKE-BACKEND MODE

Tests never use a network. For a labelled local audit, start the deterministic
fake backend (serves the generated fixtures, no live API/LLM), then build/start
Web with `NEXT_FAKE_BACKEND=1` so `/api/*` is rewritten to it:

```sh
node apps/web/scripts/fake-backend.mjs
NEXT_FAKE_BACKEND=1 pnpm --dir apps/web build
NEXT_FAKE_BACKEND=1 pnpm --dir apps/web start --port 3100
npx lighthouse http://127.0.0.1:3100/chat --only-categories=performance,accessibility,best-practices,seo
npx lighthouse http://127.0.0.1:3100/papers --only-categories=performance,accessibility,best-practices,seo
```

Every score reported in the handoff is from this explicitly labelled mode;
CI does not assert scores (L1).
