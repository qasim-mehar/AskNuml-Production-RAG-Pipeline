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
recorded in ADR 0002 (Lane E), ADR 0003 (Lanes A and B) and ADR 0004 (Lane H).
