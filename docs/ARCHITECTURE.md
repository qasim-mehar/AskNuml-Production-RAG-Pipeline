# Architecture

## System map and data flow

```mermaid
flowchart LR
  S1[University website HTML] --> A
  S2[University PDFs] --> A
  S3[Past-paper archive] --> A

  subgraph Ingestion
    A[Lane A: crawler<br/>Fetcher port] --> B[Lane B: parsers<br/>page images + question segmentation]
    B --> C[Lane C: chunking + enrichment<br/>Chunk schema / L6 fields]
  end

  C --> D[Lane D: indexing<br/>VectorStore + ObjectStore ports<br/>Postgres + Alembic migrations]
  D --> E[Lane E: retrieval]
  E --> G[Lane G: API<br/>FastAPI]
  G --> H[Lane H: web<br/>Next.js]

  F[Lane F: eval<br/>golden set + metrics + ablations + CI gate]
  F -. wraps whole pipeline .-> A
  F -.-> E

  E --- EP[Embedder / Reranker / LLM ports]
  D --- DP[VectorStore / ObjectStore ports]
  A --- FP[Fetcher / Clock ports]
```

Retrieval pipeline (Lane E), in order:

```
router → hybrid search → rerank → abstain → answer
```

- **router** classifies language (English / Urdu / Roman Urdu) and intent.
- **hybrid search** combines lexical and vector recall over the indexed chunks.
- **rerank** reorders candidates using the Reranker port.
- **abstain** applies the evidence threshold; weak evidence stops here (L13).
- **answer** generates a cited response via the LLM port, with image refs
  (e.g. past-paper pages) resolved through the ObjectStore port.

Every answer carries provenance (`source_url`, `last_crawled`, L5).

## Module boundaries

```
core ← packages ← apps
```

- `packages/core/src/uni_rag_core/` — ports (`Protocol`s), schemas, settings,
  exceptions and deterministic fakes. Depends on nothing internal.
- `packages/` — ingestion (`crawler`, `parsers`, `chunking`, `enrichment`),
  `indexing`, `retrieval`, `eval`. Depend on core only.
- `apps/` — `api` (FastAPI) and `web` (Next.js). Depend on packages (and core
  transitively). Apps never depend on other apps.
- Dependency rule (L2): dependencies point leftward. Core never imports a
  package or app; packages never import apps; domain code never imports
  infrastructure. Enforced by import-linter in CI.

## Foundation stage

At foundation stage **only interfaces and fakes exist**. Lane 0 ships the port
protocols, the `Chunk` schema, typed settings, the exception hierarchy and one
deterministic in-memory fake per port — plus their contract tests. No real
crawling, parsing, embedding, reranking, LLM calls, vector stores or model
weights are wired in yet. Lanes A–H build adapters against these frozen
contracts. Real external logic is explicitly parked (see `docs/PARKING_LOT.md`).
