# PROGRESS — Lane board

| Lane | Name | Owns | Status | Blocked by | Notes |
| --- | --- | --- | --- | --- | --- |
| 0 | Foundation | `packages/core/`, `infra/`, `.github/`, `docs/`, root config | done | — | Originally: freezing ports, schema, settings, fakes and gates. [2026-11-24] contracts frozen: 7 ports + 7 fakes, 10 schemas, typed settings, 8 lane prompts, compose + CI; all gates green except local `make up` (Docker absent on this host; compose validated statically). [2026-11-24] housekeeping: deleted `docs/AGENT.md.spec`; added L15 framework-containment contract to `.importlinter` (positive + negative checks pass); regenerated all 8 lane prompts from `docs/AGENT_ONBOARDING.md` §5; recorded ADR 0002/0003/0004 promotions in `docs/PARKING_LOT.md`; fixed CODEOWNERS default-owner pattern `/` → `*`; gates setup/lint/type/test/gate green (no `make` binary on this host, so the exact Makefile recipes were run directly). |
| A | Crawler | `packages/ingestion/crawler/` | ready | — | Originally: waits for frozen Fetcher + Clock ports. [2026-11-24] unblocked; see `docs/lanes/LANE-A.md`. [2026-11-24] ADR 0003 promotes a real HTTP Fetcher adapter tested against a local server (no live site); prompt regenerated from the eight-section template. |
| B | Parsers | `packages/ingestion/parsers/` | ready | — | Originally: page images + question segmentation. [2026-11-24] unblocked; see `docs/lanes/LANE-B.md`. [2026-11-24] ADR 0003 promotes fixture-driven Docling/MinerU parsing; prompt regenerated from the eight-section template. |
| C | Chunking & Enrichment | `packages/ingestion/chunking/`, `packages/ingestion/enrichment/` | ready | — | Originally: must honour `Chunk` / L6 metadata. [2026-11-24] unblocked; see `docs/lanes/LANE-C.md`. [2026-11-24] prompt regenerated from the eight-section template; no scope change. |
| D | Indexing | `packages/indexing/`, `infra/migrations/` | ready | — | Originally: VectorStore + ObjectStore ports; Postgres/Alembic. [2026-11-24] unblocked; see `docs/lanes/LANE-D.md`. [2026-11-24] prompt regenerated from the eight-section template; no scope change (provider adapters stay with Lane E per ADR 0002). |
| E | Retrieval | `packages/retrieval/` | ready | — | Originally: router → hybrid → rerank → abstain → answer. [2026-11-24] unblocked; see `docs/lanes/LANE-E.md`. [2026-11-24] ADR 0002 promotes `google-genai` + one second provider adapter (opt-in live calls, fakes default); prompt regenerated with L15–L17 in the law list. |
| F | Evaluation | `packages/eval/`, `eval/` | ready | — | Originally: golden set, metrics, ablations, CI gate. [2026-11-24] unblocked; see `docs/lanes/LANE-F.md`. [2026-11-24] prompt regenerated with L15–L17 in the law list; provider-comparison and graph-node eval rows per ADR 0002/L16. |
| G | API | `apps/api/` | ready | — | Originally: FastAPI. [2026-11-24] unblocked; see `docs/lanes/LANE-G.md`. [2026-11-24] prompt regenerated from the eight-section template; OpenAPI is the contract Lane H swaps in per ADR 0004; no scope change. |
| H | Web | `apps/web/` | ready | — | Originally: Next.js. [2026-11-24] unblocked; see `docs/lanes/LANE-H.md`; finder/chat UI parked. [2026-11-24] ADR 0004 promotes cited chat (streaming), past-paper finder and feedback against frozen schemas + mocked API; prompt regenerated from the eight-section template. |

## How to update

Append only — never delete history. To record a status change, append a dated
note (e.g. `[2026-11-24] status → done`) to that lane's Notes cell rather than
erasing prior entries. Do not remove rows. Lane 0 is the only writer.
