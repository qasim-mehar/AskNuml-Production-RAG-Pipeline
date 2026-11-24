# Lane E — Retrieval

You are working in the uni-rag monorepo as lane E (Retrieval).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs, including §6)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records; ADR 0002 promotes the real provider adapters)

2. MISSION
   Deliver exactly this milestone: an orchestrated retrieval pipeline
   `router → hybrid search → rerank → abstain → answer` composed only from
   injected ports, returning an `Answer` with `Citation`s and `ImageRef`s.
   Abstention must be explicit (`abstained=True`) when the top score is below
   `Settings.abstention_threshold` (L13). Build all behaviour against fakes and
   prove it before adding graph control flow. Per ADR 0002, add a `google-genai`
   adapter for `LLM`, `Embedder` and page images plus one second provider
   adapter: live calls are opt-in via settings and never run in CI, deterministic
   fakes remain the default (L17), and both adapters pass the shared contract
   test. The opt-in setting is not in core yet: Lane 0 adds it in a separate
   CONTRACT-CHANGE PR (ADR 0002); until then build and test against fakes only.
   Keep route, filter, search, rerank and answer linear; use the graph only
   for retry on weak retrieval, clarification on a missing filter, multi-hop
   answers, the abstain branch and checkpointed follow-up, one node at a time
   with an eval row (L16). No new core port, schema or setting.

3. LAW COMPLIANCE
   Laws in scope: L2, L3, L4, L6, L7, L8, L9, L12, L13, L15, L16, L17. All lanes
   are always bound by L1, L5, L10, L11 and L12. Name each law you touch. Every
   citation must include `chunk_id`, `doc_id`, `source_url` and (where present)
   `page` (L5/L6). Framework imports stay inside the planned `graph/` and
   `adapters/` directories (L15); provider behaviour stays inside its adapter
   (L17); every graph node has a named purpose and an eval row (L16).

4. FILE PLAN
   You own only: `packages/retrieval/` (including the planned
   `src/uni_rag_retrieval/graph/` and
   `src/uni_rag_retrieval/adapters/` directories). Read-only: `packages/core/`
   (Lane 0) and `packages/ingestion/`, `packages/indexing/`, `packages/eval/`,
   `apps/`, `eval/`, `infra/`, root config and all other lanes' dirs. Consume the
   frozen core ports and schemas as-is (L3); define any new Protocol domain-local,
   never in core without a CONTRACT-CHANGE PR and ADR. Create or edit nothing
   else. Consume `Embedder`, `VectorStore`, `Reranker`, `LLM`, `Clock` and
   `Settings`; define a domain-local `Searcher`/`Retriever` Protocol if needed.
   Honour `Query`, `Answer`, `Citation`, `Chunk`, `ScoredChunk`, `VectorHit` and
   `Language` as-is. Image handling uses the existing `ImageRef`/`ObjectStore`
   and adds no new core port (L3).

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: `FakeEmbedder`,
   `FakeVectorStore`, `FakeReranker`, `FakeLLM`, `FakeClock` — all deterministic,
   so routing/abstention thresholds can be tested exactly. Fixtures:
   `tests/fixtures/golden/mini-golden.json` (English, Urdu and Roman Urdu
   queries), `tests/fixtures/html/*.html`. Fakes are deterministic (L4). Unit
   tests touch no real network, LLM or paid API; live provider calls are opt-in
   only.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in
   the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly:
   ```
   uv run ruff check packages/retrieval
   uv run ruff format --check packages/retrieval
   uv run mypy packages/retrieval
   uv run pytest packages/retrieval/tests tests/contracts
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
