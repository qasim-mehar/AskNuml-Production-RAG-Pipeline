# Lane F — Evaluation

You are working in the uni-rag monorepo as lane F (Evaluation).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: a golden-set
   loader, metric functions (recall@k, MRR, precision@k, citation-accuracy),
   an ablation harness that produces a deterministic markdown table, and a CI
   gate script that fails when a measured threshold regresses. Report numbers
   only — never hard-code or invent scores (L1). Golden data comes from the
   provided mini set; generated reports are gitignored except the latest.

3. **Ownership and boundaries.** You own ONLY these dirs:
   `packages/eval/`, `eval/`.
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - `packages/ingestion/`, `packages/indexing/`, `packages/retrieval/`,
     `apps/`, `infra/`, root config and all other lanes' dirs.
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   - Consume: `Query`, `Answer`, `Citation`, `Chunk`, `Language`, `Settings`.
   - Define a domain-local `Retriever` Protocol against Lane E's service; do
     not add it to core without a CONTRACT-CHANGE PR and ADR.
   Schema names you must honour: the core schemas listed above. Use them as-is.

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: all seven fakes (`FakeEmbedder`, `FakeVectorStore`,
     `FakeReranker`, `FakeLLM`, `FakeObjectStore`, `FakeFetcher`, `FakeClock`)
     to drive a fake retrieval stack until Lane E is unblocked.
   - Fixtures: `tests/fixtures/golden/mini-golden.json` (10 questions; English,
     Urdu, Roman Urdu), `tests/fixtures/html/*.html`.
   All fakes are deterministic (L4). Do not reach for real network or models.

6. **Laws in scope.** These laws apply to your work: L1, L2, L4, L7, L9, L12.
   All lanes are always bound by L5, L10, L11 and L12 unless stated. Stratify
   reported metrics by language so Urdu/Roman Urdu regressions are visible
   (L7).

7. **Definition of done and green gates.** Run and pass exactly:
   ```
   uv run ruff check packages/eval
   uv run ruff format --check packages/eval
   uv run mypy packages/eval
   uv run pytest packages/eval/tests tests/contracts
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
