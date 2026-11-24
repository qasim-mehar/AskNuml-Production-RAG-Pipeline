# Lane B — Parsing

You are working in the uni-rag monorepo as lane B (Parsing).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records; ADR 0003 promotes the real parse adapters)

2. MISSION
   Deliver exactly this milestone: adapter interfaces for Docling (digital
   PDFs) and MinerU (scanned pages), a past-paper question segmenter producing
   `PastPaperQuestion` objects, and a page-image extractor that stores rendered
   pages through `ObjectStore` and returns `ImageRef`. Per ADR 0003, implement
   the Docling/MinerU adapters fixture-driven, validated only against checked-in
   fixtures — no real parser model or OCR is installed or called, and no live
   crawling. No new core port or schema.

3. LAW COMPLIANCE
   Laws in scope: L2, L3, L4, L6, L9, L12. All lanes are always bound by L1,
   L5, L10, L11 and L12. Name each law you touch. Every segmented question
   must retain `source_url`, `page` and an `ImageRef` so answers can cite the
   original past-paper page (L5/L6).

4. FILE PLAN
   You own only: `packages/ingestion/parsers/`. Read-only: `packages/core/`
   (Lane 0) and `packages/ingestion/crawler/`,
   `packages/ingestion/chunking/`, `packages/ingestion/enrichment/`,
   `packages/indexing/`, `packages/retrieval/`, `packages/eval/`, `apps/`,
   `eval/`, `infra/`, root config and all other lanes' dirs. Consume the frozen
   core ports and schemas as-is (L3); define any new Protocol domain-local,
   never in core without a CONTRACT-CHANGE PR and ADR. Create or edit nothing
   else. Consume `ObjectStore` (page images), `Clock` and `FetchResult`, and
   define a domain-local `DocumentParser` Protocol in your own `domain/` module.
   Honour `Document`, `PastPaperQuestion`, `ImageRef` and `FetchResult` as-is;
   domain modules must not import adapters (L2).

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: `FakeObjectStore`,
   `FakeFetcher`, `FakeClock`. Fixtures:
   `tests/fixtures/pdf/digital-course-outline.pdf` (digital),
   `tests/fixtures/pdf/scanned-past-paper-page.png` (scanned page), and
   `tests/fixtures/html/*.html`. Fakes are deterministic (L4). Unit tests
   touch no real network, LLM or paid API.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in
   the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly:
   ```
   uv run ruff check packages/ingestion/parsers
   uv run ruff format --check packages/ingestion/parsers
   uv run mypy packages/ingestion/parsers
   uv run pytest packages/ingestion/parsers/tests tests/contracts
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
