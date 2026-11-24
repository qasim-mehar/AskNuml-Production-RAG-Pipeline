# Parking Lot

Out-of-scope items for the current milestone. Do not implement these.

- Real crawling logic (network fetching at scale) — fakes and fixtures only for now.
- Real parsing logic (PDF/HTML page extraction) — fixture-driven only.
- Real embedding logic — deterministic fake embedders only.
- Real LLM logic — deterministic fake LLMs only.
- ColPali (late-interaction visual retrieval) — future work.
- Voice input/output.
- Mobile app.
- Gamification.
- Auth providers beyond a stub.
- UI beyond a health page.
- Performance tuning.
- Stale spec fallback file in `docs/` duplicates `AGENT.md` and omits L15-L17; Lane 0 to delete it.
- L15 needs a new framework import-linter contract in `.importlinter`; Lane 0 to add it.
- Regenerate `docs/lanes/*.md` prompts from the new eight-section template and add L15-L17 to the Lane E/F law lists; Lane 0 to do it.

Promotion of any item into scope requires an ADR.
