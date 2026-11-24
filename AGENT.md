# AGENT.md

Binding rules for every coding agent on `uni-rag`. Read this fully before touching code. If a rule here conflicts with a task prompt, this file wins. If a rule is wrong, open a `CONTRACT-CHANGE` PR (Lane 0) with an ADR; do not quietly break it.

## 1. What this project is

A production-grade RAG system for university students. Students ask text questions (English, Urdu, Roman Urdu) and receive cited answers plus images, especially past-paper pages. Knowledge comes from the university website (HTML and PDFs) and a past-paper archive.

The product exists to prove measurable accuracy and precision. Chunking, retrieval, search and evaluation are the showcase. Every decision must be defensible with numbers.

## 2. How we work: parallel lanes

Work is split into lanes. Each lane runs in its own conversation, on its own branch or worktree, and owns its own directories. Lanes A–H start only after Lane 0 freezes the core contracts.

| Lane | Name | Owns |
|------|------|------|
| 0 | Foundation | `packages/core/`, `infra/`, `.github/`, `docs/`, root config |
| A | Crawler | `packages/ingestion/crawler/` |
| B | Parsing | `packages/ingestion/parsers/` |
| C | Chunking and enrichment | `packages/ingestion/chunking/`, `packages/ingestion/enrichment/` |
| D | Indexing and storage | `packages/indexing/`, `infra/migrations/` |
| E | Retrieval | `packages/retrieval/` (includes planned `graph/` and provider adapters in `packages/retrieval/src/uni_rag_retrieval/adapters/`) |
| F | Evaluation | `packages/eval/`, `eval/` |
| G | API | `apps/api/` |
| H | Web | `apps/web/` |

Rules of the lane model:

- Stay in your lane. Never edit files outside your owned paths. CODEOWNERS enforces this (L14).
- Code against ports and fakes in `packages/core`, never against another lane's unfinished code. This is what keeps lanes from blocking each other.
- Need a contract changed? Open a PR touching only `packages/core` labeled `CONTRACT-CHANGE`, add an ADR, and keep working against the old contract until it merges. Only Lane 0 may merge core changes.
- Rebase on `main` at least daily. Keep PRs small and mergeable on their own.
- Lane 0 updates `docs/PROGRESS.md` (append only). Lanes do not edit docs they do not own.
- Something out of scope and tempting? Add one line to `docs/PARKING_LOT.md` and move on.

## 3. The iron laws

Every change names the laws it touches. These definitions are authoritative.

- **L1 Truth over theatre.** Prefer measurable accuracy and precision. Never fabricate metrics, scores or evidence. A change that cannot be measured is a change we do not trust.
- **L2 Layering.** `apps` depend on `packages`, never the reverse. Domain code never imports infrastructure. Enforced by import-linter in CI.
- **L3 Ports and adapters.** LLM, embedder, reranker, vector store, object store, HTTP fetcher and clock all sit behind `Protocol` classes in `packages/core/src/uni_rag_core/ports/`. An in-memory fake ships for each.
- **L4 Determinism.** Fakes, seeds and tests are deterministic. The same inputs produce the same outputs; no wall-clock or random values leak into results.
- **L5 Provenance.** Every answer is traceable to a real source URL and `last_crawled`. Cite or abstain; never invent a deadline, fee or date.
- **L6 Chunk metadata.** `Chunk` carries `chunk_id`, `doc_id`, `source_url`, `heading_path`, `content_hash`, `last_crawled`, `doc_type`, `version`, and optional `page`, `image_ref` and `metadata` (a mapping for structured producer notes such as atomic-unit reasons). `Citation.last_crawled` carries the same provenance onto answers (L5); both additions are optional for backwards compatibility (ADR 0007).
- **L7 Language parity.** English, Urdu and Roman Urdu are first-class everywhere: ingestion, retrieval, evaluation and UI.
- **L8 Config.** One typed `pydantic-settings` module (`uni_rag_core.config.settings`). No `os.environ` reads anywhere else. Settings fail fast when required values are missing.
- **L9 Small modules.** Keep modules single-purpose. Pure functions in `domain`, I/O in `adapters`, orchestration in `service`.
- **L10 Observability.** Structured JSON logging with trace ids from the first commit. No `print`.
- **L11 Errors.** Typed exception hierarchy in `uni_rag_core.errors`. No bare `except`, no swallowed exceptions.
- **L12 Tests before features.** Fixtures first, then behaviour tests. Every port adapter must pass the shared contract suite in `tests/contracts/`.
- **L13 No silent degradation.** When evidence is weak, abstain explicitly with a next step rather than guessing.
- **L14 Lane ownership.** CODEOWNERS maps every directory to its lane. Only Lane 0 touches `packages/core/`.
- **L15 Framework containment.** LangChain and LangGraph imports are allowed only in `packages/retrieval/src/uni_rag_retrieval/graph/` (planned) and `packages/retrieval/src/uni_rag_retrieval/adapters/` (provider adapters planned). The framework-free zones in §4 still apply. Framework types never cross a port. Lane 0 adds the import-linter contract that enforces this (see `docs/PARKING_LOT.md`).
- **L16 Graph nodes earn their place.** Every LangGraph node and edge has a named purpose and an eval row showing its effect. Nodes with no measurable gain are removed.
- **L17 Provider parity.** Every `LLM` and `Embedder` adapter passes the shared contract test. No provider-specific behavior leaks past its adapter.

*(The L9 numbering gap is historical; there is no second L9.)*

## 4. Code standards

- Clean, readable, boring. Prefer the obvious solution.
- No dead code, no commented-out code, no TODOs without a linked parking-lot line.
- Names say what things are; comments explain why, never what.
- DRY after the third repetition, not the first. No premature abstraction.
- Dependency injection through constructors. No globals or import-time side effects.

**Python (>= 3.11)**

- `uv` workspace, `ruff` (lint + format), `mypy --strict`, `pytest`.
- Full type hints. Pydantic v2 for every boundary datum. Ports are synchronous; adapters may use `async` internally but must honour the synchronous port signature.
- Public functions get a short docstring: purpose, non-obvious args, raises.

**TypeScript (web)**

- `pnpm`, strict TypeScript, ESLint, Vitest. No `any`.
- `lib/` holds pure functions and the API client (no React). `components/` is presentational (no fetching). `features/` composes UI with hooks.

**Frameworks**

- LangGraph runs real control flow only: retry on weak retrieval, clarification on a missing filter, multi-hop, abstain and checkpointed follow-up. Route, filter, search, rerank and answer stay linear. Department is a metadata filter and a config row, never a graph branch.
- LangChain is a utility for splitters, loaders and small integration helpers inside the retrieval adapters allowed by L15. No chains, retriever abstractions or LangChain types cross a port.
- `google-genai` is an adapter for `LLM`, `Embedder` and page images. Page-image handling lives inside the adapter: use the existing `ImageRef` schema and `ObjectStore` port for stored page images, and add no new core port (L3). A second provider must pass the same contract test; comparison is an eval run, not a graph branch.
- `packages/core/`, crawler, parsing, chunking, indexing and eval import neither framework. Graph nodes call plain service functions, so logic is unit-testable without the graph.

**Git**

- Conventional commits with a campaign tag: `type(scope): summary [campaign: name]`.
- Commit body lists Lane, Laws touched, Tests, Gates.
- One logical change per commit. Never commit failing gates.

## 5. Testing standards

- Pin behaviour, not implementation. Test names read like specs.
- Unit tests use fakes. Integration tests use docker compose. Neither touches the real internet or a paid LLM.
- Retrieval quality is measured by the eval harness, never by eyeballing.

## 6. Definition of done

A task is done only when all of these are true:

1. The mission is met and nothing outside it was built.
2. The laws touched are named and complied with.
3. Tests pin the new behaviour.
4. A fresh review subagent has done a full quality pass; its findings are resolved or logged.
5. Green gates pass in order: `make setup`, `make lint`, `make type`, `make test`, `make gate`, `make up`. The import-linter framework contract passes as part of `make gate`; Lane 0 must add it first (see `docs/PARKING_LOT.md`).
6. The commit follows the required format and `docs/PROGRESS.md` is updated by Lane 0.
7. A handoff note says what shipped, what changed in contracts, and what is next.

## 7. Never do this

- Never edit outside your lane without a CONTRACT-CHANGE PR.
- Never read config from the environment outside the settings module.
- Never call a real LLM or the live university site from a unit test.
- Never use `print` or swallow an exception to make a test pass.
- Never merge a retrieval change that lowers measured eval metrics.
- Never guess. If a requirement is ambiguous, state your assumption in the handoff and pick the safest reading.
