# Ablation summary

- variants: `12`
- backend: `fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory`
- ADR-0010 strip: `labelled in-memory boundary strip (D2 not merged)`
- corpus: `fixture-corpus-v1-integrated`
- golden set: `curated-30-v1`
- clock: `FakeClock(2026-01-01T00:00:00+00:00)`
- top_k (k): `5`
- all numbers are from the labelled integrated backend; offline adapters, no live provider. Earlier fake-backend mechanics numbers stay separate.

| variant | language | recall@5 | mrr | ndcg | faithfulness | citation_resolution | abstention_precision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dense-rerank-off-freshness-off-fixed_window+sentence_boundary | en | 0.3333 | 0.2500 | 0.2701 | 1.0000 | 1.0000 | 0.0000 |
| dense-rerank-off-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| dense-rerank-off-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.3333 | 0.3333 | 0.3333 | 0.6667 | 1.0000 | 0.1429 |
| dense-rerank-off-freshness-off-fixed_window+sentence_boundary | overall | 0.2222 | 0.1944 | 0.2011 | 0.8333 | 1.0000 | 0.0870 |
| dense-rerank-off-freshness-on-fixed_window+sentence_boundary | en | 0.3333 | 0.2500 | 0.2701 | 1.0000 | 1.0000 | 0.0000 |
| dense-rerank-off-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| dense-rerank-off-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.3333 | 0.3333 | 0.3333 | 0.6667 | 1.0000 | 0.1429 |
| dense-rerank-off-freshness-on-fixed_window+sentence_boundary | overall | 0.2222 | 0.1944 | 0.2011 | 0.8333 | 1.0000 | 0.0870 |
| dense-rerank-on-freshness-off-fixed_window+sentence_boundary | en | 0.3333 | 0.1852 | 0.2222 | 1.0000 | 1.0000 | 0.0000 |
| dense-rerank-on-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| dense-rerank-on-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.3333 | 0.3333 | 0.3333 | 0.6667 | 1.0000 | 0.1429 |
| dense-rerank-on-freshness-off-fixed_window+sentence_boundary | overall | 0.2222 | 0.1728 | 0.1852 | 0.8333 | 1.0000 | 0.0870 |
| dense-rerank-on-freshness-on-fixed_window+sentence_boundary | en | 0.3333 | 0.2037 | 0.2368 | 1.0000 | 1.0000 | 0.0000 |
| dense-rerank-on-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| dense-rerank-on-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.3333 | 0.3333 | 0.3333 | 0.6667 | 1.0000 | 0.1429 |
| dense-rerank-on-freshness-on-fixed_window+sentence_boundary | overall | 0.2222 | 0.1790 | 0.1900 | 0.8333 | 1.0000 | 0.0870 |
| hybrid-rerank-off-freshness-off-fixed_window+sentence_boundary | en | 0.5556 | 0.4667 | 0.4874 | 0.8000 | 1.0000 | 0.0000 |
| hybrid-rerank-off-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| hybrid-rerank-off-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.5556 | 0.4722 | 0.4923 | 0.6000 | 1.0000 | 0.2000 |
| hybrid-rerank-off-freshness-off-fixed_window+sentence_boundary | overall | 0.3704 | 0.3130 | 0.3266 | 0.7000 | 1.0000 | 0.1053 |
| hybrid-rerank-off-freshness-on-fixed_window+sentence_boundary | en | 0.5556 | 0.4667 | 0.4874 | 0.8000 | 1.0000 | 0.0000 |
| hybrid-rerank-off-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| hybrid-rerank-off-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.5556 | 0.4815 | 0.5000 | 0.6000 | 1.0000 | 0.2000 |
| hybrid-rerank-off-freshness-on-fixed_window+sentence_boundary | overall | 0.3704 | 0.3160 | 0.3291 | 0.7000 | 1.0000 | 0.1053 |
| hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary | en | 0.4444 | 0.2778 | 0.3179 | 0.7500 | 1.0000 | 0.0000 |
| hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.5556 | 0.4722 | 0.4923 | 0.6000 | 1.0000 | 0.2000 |
| hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary | overall | 0.3333 | 0.2500 | 0.2701 | 0.6667 | 1.0000 | 0.1000 |
| hybrid-rerank-on-freshness-on-fixed_window+sentence_boundary | en | 0.4444 | 0.2870 | 0.3256 | 0.7500 | 1.0000 | 0.0000 |
| hybrid-rerank-on-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| hybrid-rerank-on-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.5556 | 0.4722 | 0.4923 | 0.6000 | 1.0000 | 0.2000 |
| hybrid-rerank-on-freshness-on-fixed_window+sentence_boundary | overall | 0.3333 | 0.2531 | 0.2726 | 0.6667 | 1.0000 | 0.1000 |
| lexical-rerank-off-freshness-off-fixed_window+sentence_boundary | en | 0.7778 | 0.6889 | 0.7097 | 0.8571 | 1.0000 | 0.0000 |
| lexical-rerank-off-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| lexical-rerank-off-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.5556 | 0.4722 | 0.4923 | 0.6000 | 1.0000 | 0.2000 |
| lexical-rerank-off-freshness-off-fixed_window+sentence_boundary | overall | 0.4444 | 0.3870 | 0.4006 | 0.7500 | 1.0000 | 0.1176 |
| lexical-rerank-off-freshness-on-fixed_window+sentence_boundary | en | 0.7778 | 0.6889 | 0.7097 | 0.8571 | 1.0000 | 0.0000 |
| lexical-rerank-off-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| lexical-rerank-off-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.5556 | 0.4815 | 0.5000 | 0.6000 | 1.0000 | 0.2000 |
| lexical-rerank-off-freshness-on-fixed_window+sentence_boundary | overall | 0.4444 | 0.3901 | 0.4032 | 0.7500 | 1.0000 | 0.1176 |
| lexical-rerank-on-freshness-off-fixed_window+sentence_boundary | en | 0.6667 | 0.5000 | 0.5402 | 0.8333 | 1.0000 | 0.0000 |
| lexical-rerank-on-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| lexical-rerank-on-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.5556 | 0.4667 | 0.4874 | 0.6000 | 1.0000 | 0.2000 |
| lexical-rerank-on-freshness-off-fixed_window+sentence_boundary | overall | 0.4074 | 0.3222 | 0.3425 | 0.7273 | 1.0000 | 0.1111 |
| lexical-rerank-on-freshness-on-fixed_window+sentence_boundary | en | 0.6667 | 0.5093 | 0.5479 | 0.8333 | 1.0000 | 0.0000 |
| lexical-rerank-on-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| lexical-rerank-on-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.5556 | 0.4667 | 0.4874 | 0.6000 | 1.0000 | 0.2000 |
| lexical-rerank-on-freshness-on-fixed_window+sentence_boundary | overall | 0.4074 | 0.3253 | 0.3451 | 0.7273 | 1.0000 | 0.1111 |

## L16 graph-node eval rows

One row per graph node purpose. Populate from Lane E's handoff; do not invent effects.

| node | purpose | required_eval_row | measured_effect |
| --- | --- | --- | --- |
| route | Classify language, intent and metadata filters for a query. | Language + filter extraction exact-match on mini-golden.json; must not regress vs the linear baseline. | Measured: 30/30 records route to a supported language with a resolvable or intentionally empty filter; no linear-baseline regression observed. |
| filter | Apply extracted metadata filters to candidate chunks; never a graph branch. | Filter precision/recall on the crafted corpus; no golden query loses its expected doc_id. | Measured: 27/27 answerable records retain the expected doc_id after filtering. |
| search | Recall candidates with dense vectors plus in-domain lexical fusion. | recall@k and MRR vs dense-only; lexical-only uses an injected domain-local ChunkSource for full-corpus recall. | Measured hybrid-vs-dense recall@5 delta (rerank off): en +0.2222, ur +0.0000, roman_urdu +0.2222, overall +0.1481 |
| rerank | Reorder candidates through the injected Reranker port. | nDCG@10 and MRR delta against the rerank-off ablation. | Measured rerank-on minus rerank-off (hybrid) ndcg: en -0.1695, ur +0.0000, roman_urdu +0.0000, overall -0.0565. No measured gain on this corpus. |
| abstain | Emit an explicit, citation-free abstention with a next step when evidence is weak. | Abstention precision on the weak-evidence fixture; zero fabricated facts. | Measured abstention precision 0.1000 overall; the three fee rows abstain with no cited facts. |
| answer | Synthesize a cited answer whose data block is delimited and labelled. | Faithfulness and citation-resolution rate on mini-golden.json. | Measured faithfulness 0.6667 and citation-resolution 1.0000 overall (hybrid, rerank on), read natively from Citation.last_crawled. |
| retry_rewrite | Rewrite a weakly retrieved query once and repeat the search (capped loop). | recall@k gain on weak-evidence rows vs the single-pass baseline. | Measured recall@5 gain on weak-evidence rows (n=18; en 5, roman_urdu 4, ur 9): en +0.0000, ur +0.0000, roman_urdu +0.0000, overall +0.0000; L16 verdict REMOVE. |
| clarify | Ask the student for a missing required filter instead of guessing. | Clarification precision after filter-extraction errors; no needless clarifications. | awaiting measurement |
| multihop | Answer a question that must reference evidence from a second document. | Faithfulness on a two-document multi-hop fixture. | awaiting measurement |
| checkpoint_followup | Carry prior turns and citations into a checkpointed follow-up. | Citation continuity and faithfulness on a follow-up fixture. | awaiting measurement |

---

# Ablation: hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary

- backend: `fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory`
- ADR-0010 strip: `labelled in-memory boundary strip (D2 not merged)`
- corpus: `fixture-corpus-v1-integrated`
- golden set: `curated-30-v1`
- variant: `hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary` (chunking: `fixed_window+sentence_boundary`)
- clock: `FakeClock(2026-01-01T00:00:00+00:00)`
- top_k (k): `5`
- timestamp: `2026-01-01T00:00:00+00:00`
- config fingerprint: `ee224f70ada963444e2e61abc9abb019bd9bac5835c908b758d33c690c47dbbc`
- scoring: retrieval metrics pool answerable ground truth; faithfulness and citation-resolution pool answered records; abstention precision pools all records.
- first integrated-pipeline run; adapters are real but offline, no live provider or network call; a zero row is a measured result (L1).

| language | n_questions | n_answerable | n_answered | recall@5 | mrr | ndcg | faithfulness | citation_resolution | abstention_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| en | 10 | 9 | 4 | 0.4444 | 0.2778 | 0.3179 | 0.7500 | 1.0000 | 0.0000 |
| ur | 10 | 9 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| roman_urdu | 10 | 9 | 5 | 0.5556 | 0.4722 | 0.4923 | 0.6000 | 1.0000 | 0.2000 |
| overall | 30 | 27 | 9 | 0.3333 | 0.2500 | 0.2701 | 0.6667 | 1.0000 | 0.1000 |
