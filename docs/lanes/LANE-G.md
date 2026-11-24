# Lane G — API

You are working in the uni-rag monorepo as lane G (API).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: FastAPI routes for
   `POST /ask` and the existing `GET /health` / `GET /ready`, with request and
   response bodies derived from core `Query`/`Answer`, a dependency-injected
   retrieval service behind a domain-local Protocol, and trace-id middleware
   using `uni_rag_core.logging`. Parse, validate and log typed errors; never
   call a real LLM.

3. **Ownership and boundaries.** You own ONLY these dirs:
   `apps/api/`.
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - `packages/ingestion/`, `packages/indexing/`, `packages/retrieval/`,
     `packages/eval/`, `apps/web/`, `eval/`, `infra/`, root config and all other
     lanes' dirs.
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   - Consume: `Query`, `Answer`, `Citation`, `ImageRef`, `Language`,
     `get_settings()`, `get_logger()`, `trace()`, `UniRagError`,
     `ConfigError`.
   - Define a domain-local `AnswerService` Protocol in `deps/`; Lane E supplies
     the real implementation later. No real model clients here.
   Schema names you must honour: the core schemas listed above. Use them as-is.

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: `FakeLLM`, `FakeEmbedder`, `FakeVectorStore`, `FakeReranker`,
     `FakeClock` (assemble them into a fake `AnswerService` for route tests).
   - Fixtures: `tests/fixtures/golden/mini-golden.json` for representative
     request bodies.
   All fakes are deterministic (L4). Do not reach for real network or models.

6. **Laws in scope.** These laws apply to your work: L2, L3, L7, L8, L9, L10,
   L11, L12, L13. All lanes are always bound by L1, L5 and L12 unless stated.
   Apps depend on packages, never the reverse (L2). Settings come only from
   core (L8); no `print` (L10).

7. **Definition of done and green gates.** Run and pass exactly:
   ```
   uv run ruff check apps/api
   uv run ruff format --check apps/api
   uv run mypy apps/api
   uv run pytest apps/api/tests tests/contracts
   uv run lint-imports
   ```
   Then confirm `make gate` is green before handoff. Docs inside your owned
   directories must agree with code, and no parking-lot work. Lane 0 updates
   `docs/PROGRESS.md` on merge — do not edit it.

8. **Handoff.** Report back in at most 25 lines, in this format:
   - Lane / milestone:
   - Files created or changed (paths):
   - Ports implemented/consumed:
   - Gates run and result:
   - Contract issues / ADRs raised:
   - Blocked by / next lane handoff:
