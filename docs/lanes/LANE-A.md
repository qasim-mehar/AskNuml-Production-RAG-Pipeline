# Lane A — Crawler

You are working in the uni-rag monorepo as lane A (Crawler).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: a `Fetcher` adapter
   skeleton plus a deterministic URL-frontier/crawl service that turns fetched
   pages into `Document` objects carrying `doc_id`, `source_url`, `content_hash`,
   `last_crawled`, `doc_type` and `version`. De-duplicate URLs and record every
   failure as a typed error. No real network calls.

3. **Ownership and boundaries.** You own ONLY these dirs:
   `packages/ingestion/crawler/`.
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - `packages/ingestion/parsers/`, `packages/ingestion/chunking/`,
     `packages/ingestion/enrichment/`, `packages/indexing/`,
     `packages/retrieval/`, `packages/eval/`, `apps/`, `eval/`, `infra/`,
     root config and all other lanes' dirs.
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   - Implement: `Fetcher` (a skeleton adapter that accepts an injected client;
     its tests use the fake, never a socket).
   - Consume: `Clock`, `FetchResult`, `Document`, `DocType`, `ConfigError`,
     `FetchError`.
   Schema names you must honour: `Document`, `FetchResult`, plus the port-level
   request/response types defined in `packages/core/src/uni_rag_core/`. Use them
   as-is. Domain modules must not import adapters (L2).

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: `FakeFetcher` (register responses), `FakeClock` (fixed
     `last_crawled`), `FakeObjectStore` if you cache raw bytes.
   - Fixtures: `tests/fixtures/html/course-page.html`, `faculty-page.html`,
     `announcements-page.html`, `tests/fixtures/pdf/digital-course-outline.pdf`.
   All fakes are deterministic (L4). Do not reach for real network or models.

6. **Laws in scope.** These laws apply to your work: L2, L3, L4, L5, L6, L8,
   L9, L12. All lanes are always bound by L1, L5, L10, L11 and L12 unless
   stated. Get all settings through `uni_rag_core.config.get_settings()`.

7. **Definition of done and green gates.** Run and pass exactly:
   ```
   uv run ruff check packages/ingestion/crawler
   uv run ruff format --check packages/ingestion/crawler
   uv run mypy packages/ingestion/crawler
   uv run pytest packages/ingestion/crawler/tests tests/contracts
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
