# clarify: single pass vs node-on

- backend: `fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory|feedback=derived|feedback_source=fixture-transcript|live_feedback=False`
- ADR-0010 strip: `labelled in-memory boundary strip (D2 not merged)`
- clock: `FakeClock(2026-01-01T00:00:00+00:00)`
- golden set: `curated-30-plus-feedback-6-v1`
- top_k (k): `5`
- every row is a measured run; a zero or tied row is a result (L1).
- feedback input: labelled offline fixture transcript, NOT live user feedback (ADR 0009).
- corpus: `fixture-corpus-v1-integrated`
- single-pass variant: `hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary`
- node-on variant: `hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary-node=clarify-on`
- weak-evidence definition: answerable row with single-pass confidence < 0.35; composition: en 7, roman_urdu 6, ur 11 (L7)
- weak-evidence subset rule: `include-feedback-derived|source=fixture-transcript|live_feedback=False` (the six feedback-derived rows are included from the labelled offline fixture transcript, NOT live user feedback — ADR 0009).
- L16 verdict: `REMOVE` (zero or negative overall gain removes)
- scope: labelled offline backend only; the node-prompt transport echoes its prompt, so no missing filter, second-document query or carried citation is produced. No backend label claims live transport (L1/L17).
- reversal/keep condition (recorded, not acted on): Reversal of REMOVE needs a live transport that supplies a parsed missing filter (CLARIFY_DOC_ID); the offline transport only echoes its prompt.

| language | n_weak | recall@5_off | recall@5_on | gain |
| --- | --- | --- | --- | --- |
| en | 7 | 0.0000 | 0.0000 | +0.000000 |
| ur | 11 | 0.0000 | 0.0000 | +0.000000 |
| roman_urdu | 6 | 0.0000 | 0.0000 | +0.000000 |
| overall | 24 | 0.0000 | 0.0000 | +0.000000 |
