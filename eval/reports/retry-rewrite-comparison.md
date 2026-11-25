# retry_rewrite: single pass vs retry-on

- backend: `fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory`
- ADR-0010 strip: `labelled in-memory boundary strip (D2 not merged)`
- clock: `FakeClock(2026-01-01T00:00:00+00:00)`
- golden set: `curated-30-v1`
- top_k (k): `5`
- every row is a measured run; a zero or tied row is a result (L1).
- weak-evidence definition: answerable row with single-pass confidence < 0.35; composition: en 5, roman_urdu 4, ur 9 (L7)
- L16 verdict: `REMOVE` (zero or negative overall gain removes)
- scope: this verdict is for the labelled offline backend above only; the rewrite transport there echoes its prompt, so a live-provider re-run is required before treating the verdict as production evidence (opt-in, parked).

| language | n_weak | recall@5_off | recall@5_on | gain |
| --- | --- | --- | --- | --- |
| en | 5 | 0.0000 | 0.0000 | +0.000000 |
| ur | 9 | 0.0000 | 0.0000 | +0.000000 |
| roman_urdu | 4 | 0.0000 | 0.0000 | +0.000000 |
| overall | 18 | 0.0000 | 0.0000 | +0.000000 |
