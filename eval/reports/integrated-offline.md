# First integrated-pipeline numbers

- run_id: `integrated-offline-v1`
- backend: `fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|strip_source=real-adapter|ADR0010-strip`
- corpus: `fixture-corpus-v1`
- clock: `FakeClock(2026-01-01T00:00:00+00:00)` (pinned for determinism)
- golden set: `curated-30-v1`
- top_k: `5`
- no live calls: providers' live flag is off and no key is supplied through typed settings; offline transports only.
- answers are Lane E's raw pipeline outputs; no integration-side provenance patching.

| language | recall@5 | mrr | ndcg | faithfulness | abstention_precision |
| --- | --- | --- | --- | --- | --- |
| en | 0.4444 | 0.2778 | 0.3179 | 0.7500 | 0.0000 |
| roman_urdu | 0.5556 | 0.4722 | 0.4923 | 0.6000 | 0.2000 |
| ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| overall | 0.3333 | 0.2500 | 0.2701 | 0.6667 | 0.1000 |

## Baseline metric comparison

| language.metric | integrated | baseline threshold | delta |
| --- | --- | --- | --- |
| en.abstention_precision | 0.000000 | 0.000000 | +0.000000 |
| en.citation_resolution | 1.000000 | 1.000000 | +0.000000 |
| en.faithfulness | 0.750000 | 0.750000 | +0.000000 |
| en.mrr | 0.277778 | 0.277778 | +0.000000 |
| en.ndcg | 0.317928 | 0.317928 | +0.000000 |
| en.recall_at_k | 0.444444 | 0.444444 | +0.000000 |
| overall.abstention_precision | 0.100000 | 0.100000 | +0.000000 |
| overall.citation_resolution | 1.000000 | 1.000000 | +0.000000 |
| overall.faithfulness | 0.666667 | 0.666667 | +0.000000 |
| overall.mrr | 0.250000 | 0.250000 | +0.000000 |
| overall.ndcg | 0.270075 | 0.270075 | +0.000000 |
| overall.recall_at_k | 0.333333 | 0.333333 | +0.000000 |
| roman_urdu.abstention_precision | 0.200000 | 0.200000 | +0.000000 |
| roman_urdu.citation_resolution | 1.000000 | 1.000000 | +0.000000 |
| roman_urdu.faithfulness | 0.600000 | 0.600000 | +0.000000 |
| roman_urdu.mrr | 0.472222 | 0.472222 | +0.000000 |
| roman_urdu.ndcg | 0.492297 | 0.492297 | +0.000000 |
| roman_urdu.recall_at_k | 0.555556 | 0.555556 | +0.000000 |
| ur.abstention_precision | 0.100000 | 0.100000 | +0.000000 |
| ur.citation_resolution | 0.000000 | 0.000000 | +0.000000 |
| ur.faithfulness | 0.000000 | 0.000000 | +0.000000 |
| ur.mrr | 0.000000 | 0.000000 | +0.000000 |
| ur.ndcg | 0.000000 | 0.000000 | +0.000000 |
| ur.recall_at_k | 0.000000 | 0.000000 | +0.000000 |

Baseline labels differ (fake backend); label mismatches are not metric regressions. No threshold was loosened.
Gate failures recorded by Lane F's comparator: ["label backend: baseline='fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip' run='fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|strip_source=real-adapter|ADR0010-strip'", "label corpus: baseline='fixture-corpus-v1-integrated' run='fixture-corpus-v1'"]
