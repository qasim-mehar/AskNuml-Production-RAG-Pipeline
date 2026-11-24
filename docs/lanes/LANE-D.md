# Lane D — Indexing and storage

You are working in the uni-rag monorepo as lane D (Indexing and storage).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: typed adapters for
   `VectorStore` and `ObjectStore` with Qdrant/Postgres/Minio client interfaces,
   each constructed from `Settings` and passing the executable port contracts
   in `tests/contracts/port_contracts.py` with in-memory backends first. Keep the
   Alembic skeleton in `infra/migrations/` intact; add real migrations only when
   a concrete table is needed. No live infrastructure is required to test.

3. **Ownership and boundaries.** You own ONLY these dirs:
   `packages/indexing/`, `infra/migrations/`.
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - `infra/docker-compose.yml`, `infra/docker/`, all other `infra/` files,
     `packages/ingestion/`, `packages/retrieval/`, `packages/eval/`, `apps/`,
     `eval/`, root config and all other lanes' dirs.
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   - Implement: `VectorStore`, `ObjectStore`.
   - Consume: `Settings` (`get_settings()`), `Clock`, `Chunk`, `VectorHit`,
     `StorageError`.
   Schema names you must honour: `Chunk`, `VectorHit`, `ImageRef`. Use them as-is.
   Adapters live in `adapters/`; domain logic stays free of I/O (L2).

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: `FakeVectorStore`, `FakeObjectStore`, `FakeClock`, `FakeEmbedder`
     (to generate deterministic vectors for upsert).
   - Fixtures: `tests/fixtures/golden/mini-golden.json`,
     `tests/fixtures/html/*.html`.
   All fakes are deterministic (L4). Do not reach for real network or models.

6. **Laws in scope.** These laws apply to your work: L2, L3, L4, L6, L8, L9,
   L12. All lanes are always bound by L1, L5, L10, L11 and L12 unless stated.
   Read every connection value from core `Settings`; no `os.environ` (L8).

7. **Definition of done and green gates.** Run and pass exactly:
   ```
   uv run ruff check packages/indexing
   uv run ruff format --check packages/indexing
   uv run mypy packages/indexing
   uv run pytest packages/indexing/tests tests/contracts
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
