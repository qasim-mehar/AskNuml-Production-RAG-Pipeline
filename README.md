# uni-rag

A production-grade RAG system for university students. Ask a question in
English, Urdu or Roman Urdu and get a cited answer with supporting images —
especially pages from past papers. Sources are the university website (HTML and
PDFs) and the past-paper archive.

The showcase is evidence, not theatre: chunking, retrieval, search and
evaluation decisions are measurable, reproducible and defended with numbers.
Every answer is traceable to its source (`source_url`, `last_crawled`).

> Foundation stage: only interfaces (ports) and deterministic in-memory fakes
> ship today. Real adapters are built lane by lane on top of frozen contracts.

## Quickstart

```bash
# Python (managed by uv) and JS tooling
uv sync
pnpm install

# Gates
make setup    # install + bootstrap
make lint     # ruff lint/format (Python) + ESLint (web)
make type     # mypy (Python) + tsc (web)
make test     # pytest (Python) + Vitest (web)
make gate     # import-linter (L2), port contracts and core coverage
make up       # bring the stack up
make down     # bring the stack down
```

## Repo layout

```
uni-rag/
├── AGENT.md                         # binding laws, DoD, lane model, contracts
├── README.md
├── docs/
│   ├── AGENT_ONBOARDING.md          # workflow + lane prompt template
│   ├── ARCHITECTURE.md              # system map and data flow
│   ├── PROGRESS.md                  # lane board
│   ├── PARKING_LOT.md               # out-of-scope items
│   └── adr/
│       └── 0001-custom-pipeline-over-ragflow.md
├── packages/
│   ├── core/src/uni_rag_core/       # ports, schemas, settings, errors, fakes
│   │   ├── ports/                   # Protocol classes
│   │   ├── fakes/                   # one deterministic in-memory fake per port
│   │   ├── errors/                  # typed exception hierarchy
│   │   └── config/                  # settings.py (single typed settings module)
│   ├── ingestion/
│   │   ├── crawler/                 # Lane A
│   │   ├── parsers/                 # Lane B
│   │   ├── chunking/                # Lane C
│   │   └── enrichment/              # Lane C
│   ├── indexing/                    # Lane D
│   ├── retrieval/                   # Lane E
│   └── eval/                        # Lane F
├── apps/
│   ├── api/                         # Lane G (FastAPI)
│   └── web/                         # Lane H (Next.js)
├── infra/
│   └── migrations/                  # Lane D (Alembic)
├── eval/                            # Lane F (golden set, metrics, ablations)
└── .github/                         # CI, CODEOWNERS
```

## Where the contracts live

The frozen contracts are in `packages/core/src/uni_rag_core/`:

- `ports/` — `Protocol` classes for LLM, embedder, reranker, vector store,
  object store, HTTP fetcher and clock.
- `fakes/` — one deterministic in-memory fake per port; contract tests live in
  `tests/contracts/`.
- `schemas/` — `Chunk` and the other domain types, including all L6 metadata
  fields.
- `config/settings.py` — the one typed pydantic-settings module (no other
  `os.environ` reads).
- `errors/` — the typed exception hierarchy.

Only Lane 0 may change core, via a `CONTRACT-CHANGE` PR plus an ADR.

## Docs

- [AGENT.md](AGENT.md) — laws and definition of done
- [Agent onboarding](docs/AGENT_ONBOARDING.md) — workflow and prompt template
- [Architecture](docs/ARCHITECTURE.md) — system map and data flow
- [Progress](docs/PROGRESS.md) — lane board
- [Parking lot](docs/PARKING_LOT.md) — out-of-scope items
- [ADR 0001](docs/adr/0001-custom-pipeline-over-ragflow.md) — why a custom pipeline
