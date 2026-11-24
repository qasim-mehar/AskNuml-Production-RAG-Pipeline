# Spec for AGENT.md

This file is the source for the root `AGENT.md` laws. If `AGENT.md` is missing,
regenerate it from these definitions plus the lane model in
`docs/AGENT_ONBOARDING.md`. Do not change a law's meaning without a
`CONTRACT-CHANGE` PR and an ADR.

- **L1 Truth over theatre.** Measurable accuracy and precision; no fake metrics.
- **L2 Layering.** `apps` depend on `packages`, never the reverse. Domain code never imports infrastructure. Enforced by an import-linter contract in CI.
- **L3 Ports and adapters.** LLM, embedder, reranker, vector store, object store, HTTP fetcher and clock sit behind `Protocol` classes in `packages/core/src/uni_rag_core/ports/`. Ship an in-memory fake for each.
- **L4 Determinism.** Fakes and seeds are deterministic; runs are reproducible.
- **L5 Provenance.** Every answer is traceable to `source_url` and `last_crawled`.
- **L6 Chunk metadata.** `Chunk` carries `chunk_id`, `doc_id`, `source_url`, `heading_path`, `content_hash`, `last_crawled`, `doc_type`, `version`, plus an optional `page` and `image_ref`.
- **L7 Language parity.** English, Urdu and Roman Urdu are first-class.
- **L8 Config.** One typed `pydantic-settings` module. No `os.environ` reads anywhere else.
- **L9 Small modules.** Keep modules single-purpose; separate `domain`, `adapters` and `service` where applicable.
- **L10 Observability.** Structured logging with trace ids from the first commit. No `print`.
- **L11 Errors.** Typed exception hierarchy in core. No bare `except`.
- **L12 Tests before features.** Fixtures first, contract tests for every port.
- **L13 No silent degradation.** Abstain rather than guess when evidence is weak.
- **L14 Lane ownership.** CODEOWNERS maps each directory to its lane; only Lane 0 changes `packages/core/`.

The L9 numbering gap in historical drafts is not a second law.
