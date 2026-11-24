# ADR 0001 — Custom composable pipeline over RAGFlow

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)

## Context

uni-rag serves university students who ask questions in English, Urdu and
Roman Urdu and expect cited answers plus images — especially pages from past
papers. The showcase of the product is the *quality of the decisions* in
chunking, retrieval, search and evaluation: every choice must be defensible
with measurable numbers (L1). We need to run controlled ablations, swap
individual components behind ports, and reproduce runs exactly (L3, L4).
Multilingual handling and past-paper page images are first-class requirements
(L7), not nice-to-haves.

## Decision

Build a custom, composable RAG pipeline in Python. Each external concern sits
behind a `Protocol` port in core with a deterministic in-memory fake. We own the
chunking, hybrid search, reranking, abstention and evaluation layers so that
each decision can be measured, ablated and reproduced. We do not adopt RAGFlow
or any all-in-one framework as the orchestration backbone.

## Alternatives

- **RAGFlow** — an all-in-one RAG platform with built-in parsing and retrieval.
  Rejected: it does not let us prove each chunking/retrieval decision with our
  own numbers, is weak on Urdu/Roman Urdu and past-paper page images, and would
  lock evaluation behind its abstractions.
- **LlamaIndex** — a composable RAG framework. Rejected: useful as a library but
  still imposes its own abstractions over chunking and retrieval, which makes
  the strict, number-backed ablations and frozen core contracts harder to own.
- **Vanilla vector DB + prompt** — a thin index and a single LLM call. Rejected:
  no retrieval provenance guarantees, no hybrid search, no rerank/abstain stage,
  and no reproducible evaluation; it cannot satisfy L5, L10 or L13.

## Consequences

- More scaffolding up front: we must define and freeze core contracts, ship
  fakes, and build our own evaluation harness.
- Core contracts are frozen (L14); changes require a `CONTRACT-CHANGE` PR and a
  new ADR, which slows accidental churn but stabilises all lanes.
- We take full ownership of evaluation — golden set, metrics, ablations and the
  CI gate — rather than inheriting a framework's defaults.
- Accepted: the measurability, multilingual support and page-image fidelity we
  gain outweigh the extra scaffolding.
