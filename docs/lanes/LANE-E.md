# Lane E — Retrieval

You are working in the uni-rag monorepo as lane E (Retrieval).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: an orchestrated
   retrieval pipeline `router → hybrid search → rerank → abstain → answer`
   composed only from injected ports, returning an `Answer` with `Citation`s and
   `ImageRef`s. Abstention must be explicit (`abstained=True`) when the top
   score is below `Settings.abstention_threshold` (L13). No real embedding or
   LLM call; all behaviour must be reproducible with fakes.

3. **Ownership and boundaries.** You own ONLY these dirs:
   `packages/retrieval/`.
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - `packages/ingestion/`, `packages/indexing/`, `packages/eval/`, `apps/`,
     `eval/`, `infra/`, root config and all other lanes' dirs.
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   - Consume: `Embedder`, `VectorStore`, `Reranker`, `LLM`, `Clock`, `Settings`.
   - Define a domain-local `Searcher`/`Retriever` Protocol if needed; do not add
     it to core without a CONTRACT-CHANGE PR and ADR.
   Schema names you must honour: `Query`, `Answer`, `Citation`, `Chunk`,
   `ScoredChunk`, `VectorHit`, `Language`. Use them as-is.

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: `FakeEmbedder`, `FakeVectorStore`, `FakeReranker`, `FakeLLM`,
     `FakeClock` — all deterministic, so routing/abstention thresholds can be
     tested exactly.
   - Fixtures: `tests/fixtures/golden/mini-golden.json` (English, Urdu and Roman
     Urdu queries), `tests/fixtures/html/*.html`.
   All fakes are deterministic (L4). Do not reach for real network or models.

6. **Laws in scope.** These laws apply to your work: L2, L3, L4, L6, L7, L8,
   L9, L12, L13. All lanes are always bound by L1, L5, L10, L11 and L12 unless
   stated. Every citation must include `chunk_id`, `doc_id`, `source_url` and
   (where present) `page` (L5/L6).

7. **Definition of done and green gates.** Run and pass exactly:
   ```
   uv run ruff check packages/retrieval
   uv run ruff format --check packages/retrieval
   uv run mypy packages/retrieval
   uv run pytest packages/retrieval/tests tests/contracts
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
