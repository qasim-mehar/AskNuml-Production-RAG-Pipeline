# Lane C — Chunking and enrichment

You are working in the uni-rag monorepo as lane C (Chunking and enrichment).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. MISSION
   Deliver exactly this milestone: a pure, heading-aware chunker that emits
   `Chunk` objects with every mandatory L6 field (`chunk_id`, `doc_id`,
   `source_url`, `heading_path`, `content_hash`, `last_crawled`, `doc_type`,
   `version`, optional `page`/`image_ref`), plus an enrichment service that
   attaches `ImageRef` metadata and deterministic token counts. Chunk boundaries
   and hashes must be reproducible; no embedding or LLM enrichment yet.

3. LAW COMPLIANCE
   Laws in scope: L2, L4, L6, L9, L12. All lanes are always bound by L1, L5,
   L10, L11 and L12. Name each law you touch. Prove determinism with a test that
   chunks the same input twice and gets identical `chunk_id` and `content_hash`
   values (L4).

4. FILE PLAN
   You own only: `packages/ingestion/chunking/`,
   `packages/ingestion/enrichment/`. Read-only: `packages/core/` (Lane 0) and
   `packages/ingestion/crawler/`, `packages/ingestion/parsers/`,
   `packages/indexing/`, `packages/retrieval/`, `packages/eval/`, `apps/`,
   `eval/`, `infra/`, root config and all other lanes' dirs. Consume the frozen
   core ports and schemas as-is (L3); define any new Protocol domain-local,
   never in core without a CONTRACT-CHANGE PR and ADR. Create or edit nothing
   else. Consume `Clock` (stamps `last_crawled`) and `ObjectStore` (image
   lookup); chunking is pure domain logic and needs no port. Honour `Chunk`,
   `Document`, `ImageRef` and `DocType` as-is — a new field needs a
   CONTRACT-CHANGE PR with an ADR.

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: `FakeClock`,
   `FakeObjectStore`, `FakeEmbedder` (only for deterministic token/size
   estimates — do not store embeddings in `Chunk`). Fixtures:
   `tests/fixtures/html/*.html`, `tests/fixtures/golden/mini-golden.json`.
   Fakes are deterministic (L4). Unit tests touch no real network, LLM or paid
   API.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in
   the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly:
   ```
   uv run ruff check packages/ingestion/chunking packages/ingestion/enrichment
   uv run ruff format --check packages/ingestion/chunking packages/ingestion/enrichment
   uv run mypy packages/ingestion/chunking packages/ingestion/enrichment
   uv run pytest packages/ingestion/chunking/tests packages/ingestion/enrichment/tests tests/contracts
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
