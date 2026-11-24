# Lane G — API

You are working in the uni-rag monorepo as lane G (API).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records; ADR 0004 expects Lane H to mock this API)

2. MISSION
   Deliver exactly this milestone: FastAPI routes for `POST /ask` and the
   existing `GET /health` / `GET /ready`, with request and response bodies
   derived from core `Query`/`Answer`, a dependency-injected retrieval service
   behind a domain-local Protocol, and trace-id middleware using
   `uni_rag_core.logging`. Parse, validate and log typed errors; never call a
   real LLM. Publish the OpenAPI document that Lane H swaps in for its mocked
   client (ADR 0004); no new core schema or port.

3. LAW COMPLIANCE
   Laws in scope: L2, L3, L7, L8, L9, L10, L11, L12, L13. All lanes are always
   bound by L1, L5, L10, L11 and L12. Name each law you touch. Apps depend on packages,
   never the reverse (L2); settings come only from core (L8); no `print` (L10).

4. FILE PLAN
   You own only: `apps/api/`. Read-only: `packages/core/` (Lane 0) and
   `packages/ingestion/`, `packages/indexing/`, `packages/retrieval/`,
   `packages/eval/`, `apps/web/`, `eval/`, `infra/`, root config and all other
   lanes' dirs. Consume the frozen core ports and schemas as-is (L3); define any
   new Protocol domain-local, never in core without a CONTRACT-CHANGE PR and
   ADR. Create or edit nothing else. Consume `Query`, `Answer`, `Citation`,
   `ImageRef`, `Language`, `get_settings()`, `get_logger()`, `trace()`,
   `UniRagError` and `ConfigError`. Define a domain-local `AnswerService`
   Protocol in `deps/`; Lane E supplies the real implementation later. No real
   model clients here.

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: `FakeLLM`,
   `FakeEmbedder`, `FakeVectorStore`, `FakeReranker`, `FakeClock` (assemble them
   into a fake `AnswerService` for route tests). Fixtures:
   `tests/fixtures/golden/mini-golden.json` for representative request bodies.
   Fakes are deterministic (L4). Unit tests touch no real network, LLM or paid
   API.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in
   the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly:
   ```
   uv run ruff check apps/api
   uv run ruff format --check apps/api
   uv run mypy apps/api
   uv run pytest apps/api/tests tests/contracts
   uv run lint-imports
   ```
   Then confirm `make gate` is green, and commit with the campaign tag from
   `AGENT.md`. Lane 0 updates `docs/PROGRESS.md` on merge; do not edit it.

8. HANDOFF
   Report in at most 25 lines:
   - Lane / milestone:
   - Files created or changed (paths):
   - Ports implemented or consumed:
   - Gates run and result:
   - Contract issues / ADRs raised:
   - Blocked by / next lane handoff:
