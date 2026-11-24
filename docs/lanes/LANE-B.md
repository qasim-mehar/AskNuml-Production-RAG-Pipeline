# Lane B — Parsing

You are working in the uni-rag monorepo as lane B (Parsing).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: adapter interfaces
   for Docling (digital PDFs) and MinerU (scanned pages), a past-paper question
   segmenter producing `PastPaperQuestion` objects, and a page-image extractor
   that stores rendered pages through `ObjectStore` and returns `ImageRef`.
   Interfaces and fakes only — no real parser model or OCR is installed or
   called.

3. **Ownership and boundaries.** You own ONLY these dirs:
   `packages/ingestion/parsers/`.
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - `packages/ingestion/crawler/`, `packages/ingestion/chunking/`,
     `packages/ingestion/enrichment/`, `packages/indexing/`,
     `packages/retrieval/`, `packages/eval/`, `apps/`, `eval/`, `infra/`,
     root config and all other lanes' dirs.
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   - Consume: `ObjectStore` (page images), `Clock`, `FetchResult`.
   - Define a **domain-local** `DocumentParser` Protocol in your own `domain/`
     module (do not add it to core; that needs a CONTRACT-CHANGE PR and an ADR).
   Schema names you must honour: `Document`, `PastPaperQuestion`, `ImageRef`,
   `FetchResult`. Use them as-is. Domain modules must not import adapters (L2).

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: `FakeObjectStore`, `FakeFetcher`, `FakeClock`.
   - Fixtures: `tests/fixtures/pdf/digital-course-outline.pdf` (digital),
     `tests/fixtures/pdf/scanned-past-paper-page.png` (scanned page),
     `tests/fixtures/html/*.html`.
   All fakes are deterministic (L4). Do not reach for real network or models.

6. **Laws in scope.** These laws apply to your work: L2, L3, L4, L6, L9, L12.
   All lanes are always bound by L1, L5, L10, L11 and L12 unless stated. Every
   segmented question must retain `source_url`, `page` and an `ImageRef` so
   answers can cite the original past-paper page (L5/L6).

7. **Definition of done and green gates.** Run and pass exactly:
   ```
   uv run ruff check packages/ingestion/parsers
   uv run ruff format --check packages/ingestion/parsers
   uv run mypy packages/ingestion/parsers
   uv run pytest packages/ingestion/parsers/tests tests/contracts
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
