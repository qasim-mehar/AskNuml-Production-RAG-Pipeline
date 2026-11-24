# Lane F — Evaluation

You are working in the uni-rag monorepo as lane F (Evaluation).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs, including §7)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records; ADR 0002 promotes provider comparison runs)

2. MISSION
   Deliver exactly this milestone: a golden-set loader, metric functions
   (recall@k, MRR, precision@k, citation-accuracy), an ablation harness that
   produces a deterministic markdown table, and a CI gate script that fails
   when a measured threshold regresses. Report numbers only — never hard-code
   or invent scores (L1). Consume Lane E's node purposes and supply the
   required eval rows for graph nodes (L15/L16) and provider-comparison rows
   for the two adapters promoted by ADR 0002 (L17); these are eval runs, not
   graph branches. Golden data comes from the provided mini set; generated
   reports are gitignored except the latest. No live provider or network call.

3. LAW COMPLIANCE
   Laws in scope: L1, L2, L4, L7, L9, L12, L15, L16, L17. All lanes are always
   bound by L1, L5, L10, L11 and L12. Name each law you touch. Stratify reported
   metrics by language so Urdu/Roman Urdu regressions are visible (L7). The eval
   package stays framework-free (L15); provider differences are measured, not
   hard-coded into behaviour (L17); every ablation row names the node or adapter
   it measures (L16).

4. FILE PLAN
   You own only: `packages/eval/`, `eval/`. Read-only: `packages/core/` (Lane 0)
   and `packages/ingestion/`, `packages/indexing/`, `packages/retrieval/`,
   `apps/`, `infra/`, root config and all other lanes' dirs. Consume the frozen
   core ports and schemas as-is (L3); define any new Protocol domain-local,
   never in core without a CONTRACT-CHANGE PR and ADR. Create or edit nothing
   else. Consume `Query`, `Answer`, `Citation`, `Chunk`, `Language` and
   `Settings`; define a domain-local `Retriever` Protocol against Lane E's
   service rather than adding it to core.

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: all seven fakes
   (`FakeEmbedder`, `FakeVectorStore`, `FakeReranker`, `FakeLLM`,
   `FakeObjectStore`, `FakeFetcher`, `FakeClock`) to drive a fake retrieval stack
   until Lane E is unblocked. Fixtures:
   `tests/fixtures/golden/mini-golden.json` (10 questions; English, Urdu, Roman
   Urdu), `tests/fixtures/html/*.html`. Fakes are deterministic (L4). Unit tests
   touch no real network, LLM or paid API.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in
   the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly:
   ```
   uv run ruff check packages/eval
   uv run ruff format --check packages/eval
   uv run mypy packages/eval
   uv run pytest packages/eval/tests tests/contracts
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
