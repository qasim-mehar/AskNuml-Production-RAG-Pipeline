# Graph scaffold (L16) — not shipped in the default path

`RetrievalState` is a plain `TypedDict`; `NODE_REGISTRY` maps implemented node
names to plain functions in `service/pipeline.py`. No LangGraph or LangChain
symbol is imported here. `RetrievalPipeline.run` never imports this package.

A future node is added only with a named purpose and the eval row it must earn.
Lane F writes the ablation table; this file supplies the rows (L16).

| Node | Purpose | Required eval row | Status |
| --- | --- | --- | --- |
| route | Classify language, intent and metadata filters. | Language + filter exact-match on `mini-golden.json`; no regression vs linear. | mapped to `service.route_query` |
| filter | Apply metadata filters to candidate chunks (never a graph branch). | Filter precision/recall; no golden query loses its expected `doc_id`. | mapped to `service.filter_chunks` |
| search | Dense recall plus in-domain lexical fusion; an injected domain-local `ChunkSource` gives lexical-only full-corpus recall. | recall@k / MRR vs dense-only and lexical-only fixture orders. | mapped to `service.hybrid_search` |
| rerank | Reorder candidates through the Reranker port. | nDCG@10 / MRR delta vs rerank-off. | mapped to `service.rerank_candidates` |
| abstain | Explicit abstention with a next step on weak evidence. | Abstention precision; zero fabricated facts. | mapped to `service.build_abstention` |
| answer | Cited answer with a delimited, labelled data block. | Faithfulness and citation-resolution rate. | mapped to `service.synthesize_answer` |
| retry_rewrite | Grade retrieval, rewrite a weak query via the LLM port, re-search (capped). Thin wrapper over `service.retry_rewrite`. | recall@k gain vs single pass at k=5 on weak-evidence rows. | live node, mapped to `graph.nodes.retry_rewrite_node`; flag off by default until measured |
| clarify | Ask for a missing required filter. | Clarification precision; no needless clarifications. | parked until it earns the row |
| multihop | Reference evidence from a second document. | Faithfulness on a two-document fixture. | parked until it earns the row |
| checkpoint_followup | Carry prior turns and citations forward. | Citation continuity and faithfulness on a follow-up fixture. | parked until it earns the row |

First milestone for graph work: `retry_rewrite`, one node at a time.
