# PROGRESS — Lane board

| Lane | Name | Owns | Status | Blocked by | Notes |
| --- | --- | --- | --- | --- | --- |
| 0 | Foundation | `packages/core/`, `infra/`, `.github/`, `docs/`, root config | done | — | Originally: freezing ports, schema, settings, fakes and gates. [2026-11-24] contracts frozen: 7 ports + 7 fakes, 10 schemas, typed settings, 8 lane prompts, compose + CI; all gates green except local `make up` (Docker absent on this host; compose validated statically). |
| A | Crawler | `packages/ingestion/crawler/` | ready | — | Originally: waits for frozen Fetcher + Clock ports. [2026-11-24] unblocked; see `docs/lanes/LANE-A.md`. |
| B | Parsers | `packages/ingestion/parsers/` | ready | — | Originally: page images + question segmentation. [2026-11-24] unblocked; see `docs/lanes/LANE-B.md`. |
| C | Chunking & Enrichment | `packages/ingestion/chunking/`, `packages/ingestion/enrichment/` | ready | — | Originally: must honour `Chunk` / L6 metadata. [2026-11-24] unblocked; see `docs/lanes/LANE-C.md`. |
| D | Indexing | `packages/indexing/`, `infra/migrations/` | ready | — | Originally: VectorStore + ObjectStore ports; Postgres/Alembic. [2026-11-24] unblocked; see `docs/lanes/LANE-D.md`. |
| E | Retrieval | `packages/retrieval/` | ready | — | Originally: router → hybrid → rerank → abstain → answer. [2026-11-24] unblocked; see `docs/lanes/LANE-E.md`. |
| F | Evaluation | `packages/eval/`, `eval/` | ready | — | Originally: golden set, metrics, ablations, CI gate. [2026-11-24] unblocked; see `docs/lanes/LANE-F.md`. |
| G | API | `apps/api/` | ready | — | Originally: FastAPI. [2026-11-24] unblocked; see `docs/lanes/LANE-G.md`. |
| H | Web | `apps/web/` | ready | — | Originally: Next.js. [2026-11-24] unblocked; see `docs/lanes/LANE-H.md`; finder/chat UI parked. |

## How to update

Append only — never delete history. To record a status change, append a dated
note (e.g. `[2026-11-24] status → done`) to that lane's Notes cell rather than
erasing prior entries. Do not remove rows. Lane 0 is the only writer.
