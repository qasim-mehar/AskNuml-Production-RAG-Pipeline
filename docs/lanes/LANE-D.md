# Lane D — Indexing and storage

You are working in the uni-rag monorepo as lane D (Indexing and storage).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. MISSION
   Deliver exactly this milestone: typed adapters for `VectorStore` and
   `ObjectStore` with Qdrant/Postgres/Minio client interfaces, each constructed
   from `Settings` and passing the executable port contracts in
   `tests/contracts/port_contracts.py` with in-memory backends first. Keep the
   Alembic skeleton in `infra/migrations/` intact; add real migrations only when
   a concrete table is needed. No live infrastructure is required to test. Keep
   all provider code out of indexing: the `google-genai` and second-provider
   adapters belong to Lane E (ADR 0002).

3. LAW COMPLIANCE
   Laws in scope: L2, L3, L4, L6, L8, L9, L12. All lanes are always bound by
   L1, L5, L10, L11 and L12. Name each law you touch. Read every connection
   value from core `Settings`; no `os.environ` (L8).

4. FILE PLAN
   You own only: `packages/indexing/`, `infra/migrations/`. Read-only:
   `packages/core/` (Lane 0) and `infra/docker-compose.yml`, `infra/docker/`,
   all other `infra/` files, `packages/ingestion/`, `packages/retrieval/`,
   `packages/eval/`, `apps/`, `eval/`, root config and all other lanes' dirs.
   Consume the frozen core ports and schemas as-is (L3); define any new Protocol
   domain-local, never in core without a CONTRACT-CHANGE PR and ADR. Create or
   edit nothing else. Implement `VectorStore` and `ObjectStore`; consume
   `Settings` (`get_settings()`), `Clock`, `Chunk`, `VectorHit` and
   `StorageError`. Adapters live in `adapters/`; domain logic stays free of I/O
   (L2).

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: `FakeVectorStore`,
   `FakeObjectStore`, `FakeClock`, `FakeEmbedder` (to generate deterministic
   vectors for upsert). Fixtures:
   `tests/fixtures/golden/mini-golden.json`, `tests/fixtures/html/*.html`.
   Fakes are deterministic (L4). Unit tests touch no real network, LLM or paid
   API.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in
   the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly:
   ```
   uv run ruff check packages/indexing
   uv run ruff format --check packages/indexing
   uv run mypy packages/indexing
   uv run pytest packages/indexing/tests tests/contracts
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
