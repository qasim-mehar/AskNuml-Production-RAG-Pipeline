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

- [2026-11-25][done] Lane D: raw pydantic `ValidationError` on malformed stored payloads (untranslated) — the ADR-0010 boundary strip does not map storage decode failures onto `uni_rag_core.errors`; parked for a follow-up contract change. [2026-11-26] RETIRED by lane/d-indexing-m5 f709878 (LANE-0-MERGE-6): `_domain_payload` now raises core `ValidationError` with `context` (`chunk_id`, `errors`) and `__cause__`; proven by `test_malformed_stored_payload_raises_typed_core_error`.
- [2026-11-25][done] Lane D: live test probes `localhost:6333` while the client uses `settings.qdrant_url` — the reachability guard hard-codes the local port, so the live round-trip probe can disagree with configured Qdrant; parked. [2026-11-26] RETIRED by lane/d-indexing-m5 f709878 (LANE-0-MERGE-6): the guard parses `settings.qdrant_url` and the skip message names the configured endpoint; proven by `test_live_probe_follows_settings_qdrant_url`.
- [2026-11-25] Lane F: live-provider re-run of `retry_rewrite` (opt-in; reversal of `REMOVE` requires a live-transport re-run) — the zero-gain verdict is measured on the labelled offline backend only (L1/L16).
- [2026-11-25] Lane G: parsed-record persistence promotion ADR; real papers provider only after it — G3 ships the `PapersProvider` port + fake, no live provider.
- [2026-11-25] Lane G → Lane H: migration `/api/papers` → `/api/v1/papers` plus `last_crawled` — the web-client migration is a Lane H handoff, not started here.
- [2026-11-25] Lane 0: reaffirmed parked — parsed-record persistence ADR and the LangGraph dependency for `checkpoint_followup` stay queued (its L16 rows remain `awaiting measurement`); G3's promotion recommendation is input to that decision, not a promotion.

## Merge-wave handoff lines (2026-11-25, wave 4 — LANE-0-MERGE-4)

- [2026-11-25][done] Lane D: live-mode Qdrant probe stays parked — the reachability guard hard-codes `localhost:6333` while the client uses `settings.qdrant_url`, so the live round-trip probe can disagree with configured Qdrant; unchanged by the ADR-0010 real-adapter proof on the in-memory client. [2026-11-26] URL-mismatch nit RETIRED by f709878 (LANE-0-MERGE-6); the live round-trip run itself still waits on a live Qdrant service (see Docker/compose line).
- [2026-11-25] Lane F: live-transport re-run of `retry_rewrite` stays opt-in and parked — the measured KEEP/REMOVE verdict is offline-only (L1/L16); reversal of `REMOVE` requires a live-transport re-run, now that the node itself is removed in E3.
- [2026-11-25] Lane 0: compose/Docker absence stays parked — Docker is absent on this host, so the compose-backed smoke skip is expected and fails no gate; compose is validated statically only (`make up` unavailable; Makefile recipes invoked directly).
- [2026-11-25] Lane F (F4-owned, not Lane 0): stale docs still describe `retry_rewrite` as active — `eval/composition.py:6-8` and `eval/README.md:28,32,41` need updating after E3's removal; the supplied `eval/reports/latest.md` row was handed to Lane F to apply and remains F-owned, so Lane 0 did not edit `eval/` or `apps/` in this wave.
- [2026-11-25] Lane 0: reaffirmed parked — parsed-record persistence ADR and the LangGraph dependency for `checkpoint_followup` stay queued (L16 rows remain `awaiting measurement`); both are the only remaining gates for G4 and H migration, and neither was promoted here.

## Checkpoint follow-up decisions (2026-11-26)

- [2026-11-26][done] Lane 0: parsed-record persistence PROMOTED by ADR 0011 — closes this line and the 2026-11-25 "Lane G: parsed-record persistence promotion ADR; real papers provider only after it" line, plus Lane B's 2026-11-24 lines 23 and 39. What is persisted: parsed `PaperRecord`s with frozen `source_url` / `last_crawled` / `page` and a resolvable `image_ref`; where: Lane D's Postgres `MetadataStore` plus a new Alembic revision, page images in `ObjectStore`, Qdrant vector-only per ADR 0010; rule: the papers provider goes real only post-persistence. G4 and Lane H migration are green.
- [2026-11-26][done] Lane E: LangGraph dependency CLOSED as **not adopted** — closes the queued dependency question (2026-11-25 lines 78/86 and the 2026-11-24 line 41's dependency aspect). E2's registry-only design (`packages/retrieval/src/uni_rag_retrieval/graph/nodes.py`) satisfies L15 trivially with plain `service` functions and no framework import; F4, G4 and H migration need no graph orchestration. Reopen **only if a node-orchestration requirement emerges** — a future node with a named purpose and a measured L16 eval-row gain that needs real control flow (branching, loops or checkpointed follow-up). Do not re-queue this at every checkpoint.
- [2026-11-26] Lane 0: this campaign's promotions are now ADR 0002, 0003, 0004, 0005–0009, plus ADR 0010 (Lane D) and ADR 0011 (parsed-record persistence); the remaining reaffirmed-parked lines stand except where closed above.
- [2026-11-26] Lane 0: parsed-record persistence does not promote live crawling or live parsing (ADR 0003); fixture-only scope stands.

## Merge-wave handoff lines (2026-11-26 — LANE-0-MERGE-5)

- [2026-11-26] Lane A/B: live crawling and live parsing stay parked — ADR 0003 keeps fixture/local-server scope; ADR 0011 persistence does not promote either.
- [2026-11-26] Lane F/H: feedback auth/persistence and real (non-fixture) feedback ingestion stay parked — ADR 0009 grants only the local-only `202` echo; F4's six derived rows come from a labelled fixture transcript, never live users.
- [2026-11-26] Lane F: opt-in live-provider `retry_rewrite` re-run stays parked — the E3 `REMOVE` verdict is offline-only and reversal requires a live-transport measurement (L1/L16).
- [2026-11-26] Lane E/F: live-transport provider comparison stays parked — provider parity is contract-tested offline; comparison is an opt-in eval run, not a graph branch.
- [2026-11-26][done] Lane D: live-mode Qdrant probe stays parked — the reachability guard hard-codes `localhost:6333` while the client uses `settings.qdrant_url`; unchanged by G4's metadata-store work. [2026-11-26] URL-mismatch nit RETIRED by f709878 (LANE-0-MERGE-6); the live round-trip run itself stays parked with the other live-* items.
- [2026-11-26] Lane 0: compose/Docker absence stays parked — no Docker binary on this host, so `make up` is unavailable; Makefile recipes were invoked directly and compose YAML validated statically.
- [2026-11-26][done] Lane D (reaffirmed nits): raw pydantic `ValidationError` on malformed stored payloads remains untranslated; the live-probe URL mismatch remains as above. [2026-11-26] BOTH RETIRED by f709878 (LANE-0-MERGE-6): typed core `ValidationError` with context/`__cause__`, and a probe that follows `settings.qdrant_url` and names it in the skip message.
- [2026-11-26] Lane 0: next-milestone candidates are the `awaiting measurement` L16 rows for `clarify` and `multihop` (per the checkpoint's LangGraph close note) plus D's two logged nits; the LangGraph dependency itself stays CLOSED as not adopted. Everything live-* stays parked. [2026-11-26] SUPERSEDED by LANE-0-MERGE-6: F5 b42e8a2 measured `clarify`, `multihop` and `checkpoint_followup` (all +0.0000 overall, L16 REMOVE) and f709878 retired D's two nits; no candidate from this line remains open.
- [2026-11-26] Lane 0 (stash reconciliation): G4 safety stash 5ccc57f dropped as fully subsumed by lane/h-web-m4 4296728 — five web files with identical `routes.ts` blob and H's tree a strict superset, no untracked parent. The two original pre-existing stashes (MERGE-3 safety, Lane0 shared-checkout) were left untouched. The unattributed third stash F4 reported is not present in `refs/stash` nor as an unreachable stash-like commit; flagged, nothing dropped on speculation.
- [2026-11-26] Lane 0 (consistency): H's emitted fixtures were re-derived from the merged openapi.json byte-deterministically with zero diffs (`core-emitted.json` blob 9edf2006…, `openapi-emitted.json` blob 3f2a38cd…); no wording moved and web gates remain green.
- [2026-11-26] Lane 0 (L14 sign-off): `tests/contracts/parsed_record_contract.py` and `tests/contracts/test_parsed_record_roundtrip.py` reviewed and signed off — no blocking findings; nits logged only (helper docstring overstates reuse, `upgrade` outside `try/finally`, status asserted after indexing results).

## Merge-wave handoff lines (2026-11-26 — LANE-0-MERGE-6)

- [2026-11-26] Lane 0: both D nits are RETIRED by f709878 (see the dated closure notes above) — the untranslated stored-payload `ValidationError` and the `localhost:6333` probe mismatch are closed; the two original stashes were left untouched and no new stash was created.
- [2026-11-26] Lane A/B: live crawling and live parsing stay parked — ADR 0003 keeps fixture/local-server scope; ADR 0011 persistence does not promote either.
- [2026-11-26] Lane E/F/G/H: every live-* item stays parked — live-provider comparison, opt-in live `retry_rewrite` re-run and reversal of its (or F5's three) L16 verdicts, live user-feedback ingestion/auth and real-LLM faithfulness judge, Crawl4AI/live-network parsing, real auth providers and live image proxy. F5's three node-on measurements are labelled-offline echo transports only (L1/L16); no live transport ran in this wave.
- [2026-11-26] Lane 0: compose/Docker absence stays parked — no Docker binary on this host, so `make up` is unavailable; Makefile recipes were invoked directly (no `make` binary either) and compose YAML validated statically only. The live-mode Qdrant round-trip run stays parked with it; f709878 fixed only which URL the guard probes.
- [2026-11-26] Lane 0: parsed-record persistence promotion and the LangGraph dependency stay as previously decided (ADR 0011 promoted; LangGraph CLOSED as not adopted) — this wave changed no ADR and promoted nothing.

## Merge-wave handoff lines (2026-11-26 — LANE-0-MERGE-7)

- [2026-11-26] Lane E/F: reversal of E5's `clarify` L16 REMOVE verdict is parked — it requires a live-transport re-run that actually supplies a parsed missing filter (`CLARIFY_DOC_ID`); F5's labelled-offline echo transport only echoes its prompt, so its +0.0000 recall@5 gain is not evidence against the node on a live transport (L1/L16). No substitute node, retry, clarification or follow-up logic may be added before such a measured gain exists.
- [2026-11-26] Lane E/F: reversal of E5's `multihop` L16 REMOVE verdict is parked — it requires a live-transport re-run that actually supplies a second-document query (`MULTIHOP_QUERY`); the offline transport only echoes its prompt, so the +0.0000 recall@5 gain does not settle the live-transport case (L1/L16).
- [2026-11-26] Lane E/F: reversal of E5's `checkpoint_followup` L16 REMOVE verdict is parked — it requires a live-transport re-run that actually supplies carried citation ids (`FOLLOWUP_CITATIONS`); the offline transport only echoes its prompt (L1/L16). The LangGraph dependency stays CLOSED as not adopted; reopen only if a node-orchestration requirement emerges with a measured L16 gain.
- [2026-11-26] Lane 0: no ADR promoted and no lane code edited by this wave — E5 removed the three registry/README/state entries only; its supplied `eval/reports/latest.md` rows for the three nodes and the `LANE_E_NODE_ROWS` / `test_ablation.py` / `eval/README.md` reconciliation stay F-owned for F6, which pins to this wave's head. Live-* items, compose/Docker absence and the two pre-existing stashes all stay as previously parked and untouched.
