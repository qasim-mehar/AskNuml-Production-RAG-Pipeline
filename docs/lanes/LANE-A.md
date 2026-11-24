# Lane A — Crawler

You are working in the uni-rag monorepo as lane A (Crawler).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records; ADR 0003 promotes the real fetch adapter)

2. MISSION
   Deliver exactly this milestone: a `Fetcher` adapter skeleton plus a
   deterministic URL-frontier/crawl service that turns fetched pages into
   `Document` objects carrying `doc_id`, `source_url`, `content_hash`,
   `last_crawled`, `doc_type` and `version`. De-duplicate URLs and record every
   failure as a typed error. Per ADR 0003, add a real HTTP `Fetcher` adapter
   exercised against a local test server; large-scale live crawling of the
   university site stays parked. No real network calls outside the local test
   server and no new core port or schema.

3. LAW COMPLIANCE
   Laws in scope: L2, L3, L4, L5, L6, L8, L9, L12. All lanes are always bound by
   L1, L5, L10, L11 and L12. Name each law you touch. Get all settings through
   `uni_rag_core.config.get_settings()` (L8); domain modules must not import
   adapters (L2).

4. FILE PLAN
   You own only: `packages/ingestion/crawler/`. Read-only: `packages/core/`
   (Lane 0) and `packages/ingestion/parsers/`,
   `packages/ingestion/chunking/`, `packages/ingestion/enrichment/`,
   `packages/indexing/`, `packages/retrieval/`, `packages/eval/`, `apps/`,
   `eval/`, `infra/`, root config and all other lanes' dirs. Consume the frozen
   core ports and schemas as-is (L3); define any new Protocol domain-local,
   never in core without a CONTRACT-CHANGE PR and ADR. Create or edit nothing
   else. Implement `Fetcher` with an injected client; consume `Clock`,
   `FetchResult`, `Document`, `DocType`, `ConfigError` and `FetchError`.

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: `FakeFetcher` (register
   responses), `FakeClock` (fixed `last_crawled`), `FakeObjectStore` if you cache
   raw bytes. Fixtures: `tests/fixtures/html/course-page.html`,
   `faculty-page.html`, `announcements-page.html`, and
   `tests/fixtures/pdf/digital-course-outline.pdf`; exercise the real adapter
   against a local test server only. Fakes are deterministic (L4). Unit tests
   touch no real network, LLM or paid API.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in
   the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly:
   ```
   uv run ruff check packages/ingestion/crawler
   uv run ruff format --check packages/ingestion/crawler
   uv run mypy packages/ingestion/crawler
   uv run pytest packages/ingestion/crawler/tests tests/contracts
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
