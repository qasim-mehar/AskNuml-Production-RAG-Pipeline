# Parking Lot

Out-of-scope items for the current milestone. Do not implement these unless
promoted by an ADR (L1).

- Real crawling logic at scale against the live university site — still parked. A fixture/local-test-server HTTP `Fetcher` adapter for Lane A is promoted by ADR 0003.
- Real parsing logic (PDF/HTML page extraction) — fixture-driven Docling (digital) and MinerU (scanned) adapters for Lane B promoted by ADR 0003; no live site.
- Real embedding logic — deterministic fake embedders remain the default; real `google-genai` and one second provider adapter for Lane E promoted by ADR 0002.
- Real LLM logic — promoted to Lane E by ADR 0002: opt-in via settings (setting pending a separate Lane 0 CONTRACT-CHANGE PR), never in CI; fakes remain the default (L17).
- ColPali (late-interaction visual retrieval) — future work.
- Voice input/output.
- Mobile app.
- Gamification.
- Auth providers beyond a stub.
- UI beyond a health page — promoted to Lane H by ADR 0004 (cited chat with streaming, past-paper finder, feedback) against the frozen `Query`/`Answer` schemas and a mocked API until Lane G's OpenAPI lands.
- Performance tuning.
- [2026-11-24][done] Lane 0: stale spec fallback file `docs/AGENT.md.spec` deleted (it duplicated `AGENT.md` and omitted L15–L17).
- [2026-11-24][done] Lane 0: L15 framework import-linter contract added to `.importlinter`, covering planned `graph/` and `adapters/` as allowed paths.
- [2026-11-24][done] Lane 0: `docs/lanes/LANE-A.md` … `LANE-H.md` regenerated from the eight-section template in `docs/AGENT_ONBOARDING.md` §5; L15–L17 added to the Lane E/F law lists.
- [2026-11-24] Lane B: MinerU is parked — no installable wheel is available offline and no OCR is faked. Fallback: `MinerUParser` keeps the engine interface and, for fixtures only, reads a checked-in transcription sidecar plus the scanned PNG; no real OCR runs (L1, L4).
- [2026-11-24] Lane B: OCR for handwriting and for non-past-paper archives is out of scope.
- [2026-11-24] Lane B: parsing anything fetched live from the network is out of scope; fixtures only (L4).
- [2026-11-24] Lane B: storing parsed records in Postgres/Qdrant is out of scope (Lane D).
- [2026-11-24] Lane B: no PDF/HTML page renderer is available offline, so digital pages get a deterministic placeholder PNG (explicit caption) instead of a rendered image until a renderer is added.

Promotion of any item into scope requires an ADR. This campaign's promotions are
recorded in ADR 0002 (Lane E), ADR 0003 (Lanes A and B), ADR 0004 (Lane H) and
ADRs 0005–0009 (Lane 0 contracts wave).

## Merge-wave handoff lines (2026-11-24)

- [2026-11-24] Lane A: Live crawl smoke script (opt-in, after a live-crawl ADR).
- [2026-11-24] Lane A: Crawl4AI integration.
- [2026-11-24] Lane A: Sitemap discovery.
- [2026-11-24] Lane A: Postgres crawl-state persistence.
- [2026-11-24] Lane B: MinerU adapter wiring (no installable wheel offline; interface ready; transcription fallback shipped).
- [2026-11-24] Lane B: OCR beyond fixture transcription.
- [2026-11-24] Lane B: Live-network parsing.
- [2026-11-24] Lane B: Parsed-record persistence in Postgres/Qdrant.
- [2026-11-24] Lane B: Real page scans replacing placeholder images.
- [2026-11-24] Lane E: LangGraph nodes one at a time, each with its measured eval row; retry_rewrite first.
- [2026-11-24] Lane E: Grounded-citation-usage check.
- [2026-11-24] Lane E: Narrow provider adapters to SDK exception types (replace except Exception).
- [2026-11-24] Lane E: Live provider comparison run (opt-in, never CI).
- [2026-11-24] Lane F: Real feedback-to-golden ingestion.
- [2026-11-24] Lane F: Opt-in real-LLM faithfulness judge (never CI).
- [2026-11-24] Lane G: Real auth providers beyond the API-key stub.
- [2026-11-24] Lane H: Scaling, deployment and horizontal concerns.
- [2026-11-24] Lane D: Document-level soft-delete method in the metadata store.
- [2026-11-24] Lane 0: Windows make parity (run recipes directly when the binary is absent).
- [2026-11-24] Lane 0: feedback persistence, golden-set ingestion and any feedback auth remain parked; ADR 0009 grants only the local-only `202` echo route with structured logging (Lane F milestone).
- [2026-11-24] Lane 0: SSE envelopes (`TokenEvent`, `CitationsEvent`) stay API-local by ADR 0009; no core port or schema promotion.
- [2026-11-24] Lane 0: lockfile regeneration stays parked until a network-enabled host; ADR 0005 is the authoritative pin inventory. Docling remains unpinned and undeclared (candidate `2.152.0` recorded from the ledger; no wheel resolvable offline).
- [2026-11-24] Lane 0: lane shims retire in each lane's next milestone, not this wave — A's `CrawlerConfig`/`conditional_headers_for` and local `SystemClock`, B's `PaperMetadata`/parser-local `ParsedDocument`, C's chunking-local `ParsedDocument` and text atomic-unit reasons, E's last-crawled/next-step text footers, G's `ApiSettings`/API-local error subclasses, H's strict TS mirrors and `core-emitted.json` fixture (ADRs 0006–0009).
- [2026-11-24] Lane 0: generation of a real page-image renderer and a live `/api/images/{ref_id}` proxy implementation stay parked; `ImageRef.image_url` only documents the convention (ADR 0007).
- [2026-11-25] Lane D: exposing the nine operational payload fields (`last_crawled_ts`, `department`, `course_code`, `year`, `term`, `is_live`, `indexed_at`, `deleted_at`, `superseded_by`) as first-class `Chunk` fields stays parked. ADR 0010 keeps them in Qdrant storage for filter pushdown and strips them from `VectorHit.payload` at the adapter boundary; no core schema or L6 change. One-line fix request routed to Lane D in the handoff.

## Merge-wave handoff lines (2026-11-25, wave 2)

- [2026-11-25] Lane H: user-visible fake-backend banner — the labelled local Lighthouse mode is honest in docs/logs but the UI does not tell a visitor the backend is fake.
- [2026-11-25] Lane H: localized image-failure copy — a failed image load becomes an explicit status message, but only in English (L7).
- [2026-11-25] Lane H: configurable SSE timeout — `DEFAULT_TIMEOUT_MS` / `STREAM_TIMEOUT_MS` are hard-coded in the web client.
- [2026-11-25] Lane H: feedback auth/persistence — H2 keeps ADR 0009's local-only `202` echo; real feedback auth and persistence stay parked (reaffirms the 2026-11-24 line).
- [2026-11-25] Lane F: live-provider comparison run (opt-in, never CI) — carried from F2's proposals. (F2's per-strategy corpus differentiation is being executed in F3 and is deliberately not parked; recorded on the PROGRESS board only.)
- [2026-11-25] Lane G: per-package `py.typed` markers for D and E — D2 takes D's marker; E's marker waits for E3 (core's marker already shipped in ADR 0008).
- [2026-11-25] Lane G → G3: declare `x-request-id` on every OpenAPI operation; G2's regenerated artifact omits it. G3 also owns the real residuals from H2's reconciliation — the papers route is absent and the two SSE envelopes are undocumented.
- [2026-11-25][done] Lane E: narrow provider adapters to SDK exception types (closes the 2026-11-24 line) — landed with E2 (24921d5, merge 78d7597).
- [2026-11-25][done] Lane E: `Citation.last_crawled` population — E2 reads it natively from the ADR 0007 provenance fields; no residual remains.
- [2026-11-25][done] Lane 0: lockfile regeneration (closes the 2026-11-24 parked line) — `uv.lock` regenerated with the full declared dependency set including G2's API deps and `live` extra; `uv lock --check` green on a network-enabled host. ADR 0005 remains the pin inventory; Docling remains unpinned and undeclared.

## Merge-wave handoff lines (2026-11-25, wave 6 — LANE-0-MERGE-3)

- [2026-11-25] Lane D: raw pydantic `ValidationError` on malformed stored payloads (untranslated) — the ADR-0010 boundary strip does not map storage decode failures onto `uni_rag_core.errors`; parked for a follow-up contract change.
- [2026-11-25] Lane D: live test probes `localhost:6333` while the client uses `settings.qdrant_url` — the reachability guard hard-codes the local port, so the live round-trip probe can disagree with configured Qdrant; parked.
- [2026-11-25] Lane F: live-provider re-run of `retry_rewrite` (opt-in; reversal of `REMOVE` requires a live-transport re-run) — the zero-gain verdict is measured on the labelled offline backend only (L1/L16).
- [2026-11-25] Lane G: parsed-record persistence promotion ADR; real papers provider only after it — G3 ships the `PapersProvider` port + fake, no live provider.
- [2026-11-25] Lane G → Lane H: migration `/api/papers` → `/api/v1/papers` plus `last_crawled` — the web-client migration is a Lane H handoff, not started here.
- [2026-11-25] Lane 0: reaffirmed parked — parsed-record persistence ADR and the LangGraph dependency for `checkpoint_followup` stay queued (its L16 rows remain `awaiting measurement`); G3's promotion recommendation is input to that decision, not a promotion.
