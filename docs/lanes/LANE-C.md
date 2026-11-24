# Lane C — Chunking and enrichment

You are working in the uni-rag monorepo as lane C (Chunking and enrichment).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: a pure,
   heading-aware chunker that emits `Chunk` objects with every mandatory L6
   field (`chunk_id`, `doc_id`, `source_url`, `heading_path`, `content_hash`,
   `last_crawled`, `doc_type`, `version`, optional `page`/`image_ref`), plus an
   enrichment service that attaches `ImageRef` metadata and deterministic
   token counts. Chunk boundaries and hashes must be reproducible; no embedding
   or LLM enrichment yet.

3. **Ownership and boundaries.** You own ONLY these dirs:
   `packages/ingestion/chunking/`, `packages/ingestion/enrichment/`.
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - `packages/ingestion/crawler/`, `packages/ingestion/parsers/`,
     `packages/indexing/`, `packages/retrieval/`, `packages/eval/`, `apps/`,
     `eval/`, `infra/`, root config and all other lanes' dirs.
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   - Consume: `Clock` (stamps `last_crawled`), `ObjectStore` (image lookup).
   - Chunking is pure domain logic; no port is needed to produce chunks.
   Schema names you must honour: `Chunk`, `Document`, `ImageRef`, `DocType`.
   Use them as-is. If you need a new field in `Chunk`, open a CONTRACT-CHANGE PR
   with an ADR — do not patch around the frozen schema.

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: `FakeClock`, `FakeObjectStore`, `FakeEmbedder` (only for deterministic
     token/size estimates — do not store embeddings in `Chunk`).
   - Fixtures: `tests/fixtures/html/*.html`,
     `tests/fixtures/golden/mini-golden.json`.
   All fakes are deterministic (L4). Do not reach for real network or models.

6. **Laws in scope.** These laws apply to your work: L2, L4, L6, L9, L12.
   All lanes are always bound by L1, L5, L10, L11 and L12 unless stated. Prove
   determinism with a test that chunks the same input twice and gets identical
   `chunk_id` and `content_hash` values.

7. **Definition of done and green gates.** Run and pass exactly:
   ```
   uv run ruff check packages/ingestion/chunking packages/ingestion/enrichment
   uv run ruff format --check packages/ingestion/chunking packages/ingestion/enrichment
   uv run mypy packages/ingestion/chunking packages/ingestion/enrichment
   uv run pytest packages/ingestion/chunking/tests packages/ingestion/enrichment/tests tests/contracts
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
