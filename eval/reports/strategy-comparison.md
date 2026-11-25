# Chunking strategy ablation: per-strategy corpora

- backend: `fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory`
- ADR-0010 strip: `labelled in-memory boundary strip (D2 not merged)`
- clock: `FakeClock(2026-01-01T00:00:00+00:00)`
- golden set: `curated-30-v1`
- top_k (k): `5`
- every row is a measured run; a zero or tied row is a result (L1).
- corpora: the same fixture documents indexed once under fixed_window and once under sentence_boundary; each strategy queried against its own corpus.
- chunk-id sets are distinct by construction; golden ids are translated into each corpus so no reference dangles (L12).
- differential effect: measured non-zero delta

| language | corpus_fixed_window | corpus_sentence_boundary | gain |
| --- | --- | --- | --- |
| en | 0.4444 | 0.0833 | -0.3611 |
| ur | 0.0000 | 0.0000 | +0.0000 |
| roman_urdu | 0.5556 | 0.0926 | -0.4630 |
| overall | 0.3333 | 0.0586 | -0.2747 |
