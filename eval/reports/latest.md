# Ablation summary

- variants: `12`
- backend: `fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory|feedback=derived|feedback_source=fixture-transcript|live_feedback=False`
- ADR-0010 strip: `labelled in-memory boundary strip (D2 not merged)`
- corpus: `fixture-corpus-v1-integrated`
- golden set: `curated-30-plus-feedback-6-v1`
- clock: `FakeClock(2026-01-01T00:00:00+00:00)`
- top_k (k): `5`
- feedback input: labelled offline fixture transcript, NOT live user feedback (ADR 0009).
- all numbers are from the labelled integrated backend; offline adapters, no live provider. Earlier fake-backend mechanics numbers stay separate.

| variant | language | recall@5 | mrr | ndcg | faithfulness | citation_resolution | abstention_precision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dense-rerank-off-freshness-off-fixed_window+sentence_boundary | en | 0.2727 | 0.2045 | 0.2210 | 1.0000 | 1.0000 | 0.0000 |
| dense-rerank-off-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| dense-rerank-off-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.2727 | 0.2727 | 0.2727 | 0.6667 | 1.0000 | 0.1111 |
| dense-rerank-off-freshness-off-fixed_window+sentence_boundary | overall | 0.1818 | 0.1591 | 0.1646 | 0.8333 | 1.0000 | 0.0690 |
| dense-rerank-off-freshness-on-fixed_window+sentence_boundary | en | 0.2727 | 0.2045 | 0.2210 | 1.0000 | 1.0000 | 0.0000 |
| dense-rerank-off-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| dense-rerank-off-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.2727 | 0.2727 | 0.2727 | 0.6667 | 1.0000 | 0.1111 |
| dense-rerank-off-freshness-on-fixed_window+sentence_boundary | overall | 0.1818 | 0.1591 | 0.1646 | 0.8333 | 1.0000 | 0.0690 |
| dense-rerank-on-freshness-off-fixed_window+sentence_boundary | en | 0.2727 | 0.1515 | 0.1818 | 1.0000 | 1.0000 | 0.0000 |
| dense-rerank-on-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| dense-rerank-on-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.2727 | 0.2727 | 0.2727 | 0.6667 | 1.0000 | 0.1111 |
| dense-rerank-on-freshness-off-fixed_window+sentence_boundary | overall | 0.1818 | 0.1414 | 0.1515 | 0.8333 | 1.0000 | 0.0690 |
| dense-rerank-on-freshness-on-fixed_window+sentence_boundary | en | 0.2727 | 0.1667 | 0.1937 | 1.0000 | 1.0000 | 0.0000 |
| dense-rerank-on-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| dense-rerank-on-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.2727 | 0.2727 | 0.2727 | 0.6667 | 1.0000 | 0.1111 |
| dense-rerank-on-freshness-on-fixed_window+sentence_boundary | overall | 0.1818 | 0.1465 | 0.1555 | 0.8333 | 1.0000 | 0.0690 |
| hybrid-rerank-off-freshness-off-fixed_window+sentence_boundary | en | 0.4545 | 0.3818 | 0.3988 | 0.8000 | 1.0000 | 0.0000 |
| hybrid-rerank-off-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| hybrid-rerank-off-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.4545 | 0.3864 | 0.4028 | 0.6000 | 1.0000 | 0.1429 |
| hybrid-rerank-off-freshness-off-fixed_window+sentence_boundary | overall | 0.3030 | 0.2561 | 0.2672 | 0.7000 | 1.0000 | 0.0800 |
| hybrid-rerank-off-freshness-on-fixed_window+sentence_boundary | en | 0.4545 | 0.3818 | 0.3988 | 0.8000 | 1.0000 | 0.0000 |
| hybrid-rerank-off-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| hybrid-rerank-off-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.4545 | 0.3939 | 0.4091 | 0.6000 | 1.0000 | 0.1429 |
| hybrid-rerank-off-freshness-on-fixed_window+sentence_boundary | overall | 0.3030 | 0.2586 | 0.2693 | 0.7000 | 1.0000 | 0.0800 |
| hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary | en | 0.3636 | 0.2273 | 0.2601 | 0.7500 | 1.0000 | 0.0000 |
| hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.4545 | 0.3864 | 0.4028 | 0.6000 | 1.0000 | 0.1429 |
| hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary | overall | 0.2727 | 0.2045 | 0.2210 | 0.6667 | 1.0000 | 0.0769 |
| hybrid-rerank-on-freshness-on-fixed_window+sentence_boundary | en | 0.3636 | 0.2348 | 0.2664 | 0.7500 | 1.0000 | 0.0000 |
| hybrid-rerank-on-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| hybrid-rerank-on-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.4545 | 0.3864 | 0.4028 | 0.6000 | 1.0000 | 0.1429 |
| hybrid-rerank-on-freshness-on-fixed_window+sentence_boundary | overall | 0.2727 | 0.2071 | 0.2231 | 0.6667 | 1.0000 | 0.0769 |
| lexical-rerank-off-freshness-off-fixed_window+sentence_boundary | en | 0.7273 | 0.6545 | 0.6715 | 0.8750 | 1.0000 | 0.0000 |
| lexical-rerank-off-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| lexical-rerank-off-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.4545 | 0.3864 | 0.4028 | 0.6000 | 1.0000 | 0.1429 |
| lexical-rerank-off-freshness-off-fixed_window+sentence_boundary | overall | 0.3939 | 0.3470 | 0.3581 | 0.7692 | 1.0000 | 0.0909 |
| lexical-rerank-off-freshness-on-fixed_window+sentence_boundary | en | 0.7273 | 0.6545 | 0.6715 | 0.8750 | 1.0000 | 0.0000 |
| lexical-rerank-off-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| lexical-rerank-off-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.4545 | 0.3939 | 0.4091 | 0.6000 | 1.0000 | 0.1429 |
| lexical-rerank-off-freshness-on-fixed_window+sentence_boundary | overall | 0.3939 | 0.3495 | 0.3602 | 0.7692 | 1.0000 | 0.0909 |
| lexical-rerank-on-freshness-off-fixed_window+sentence_boundary | en | 0.6364 | 0.5000 | 0.5329 | 0.8571 | 1.0000 | 0.0000 |
| lexical-rerank-on-freshness-off-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| lexical-rerank-on-freshness-off-fixed_window+sentence_boundary | roman_urdu | 0.4545 | 0.3818 | 0.3988 | 0.6000 | 1.0000 | 0.1429 |
| lexical-rerank-on-freshness-off-fixed_window+sentence_boundary | overall | 0.3636 | 0.2939 | 0.3106 | 0.7500 | 1.0000 | 0.0870 |
| lexical-rerank-on-freshness-on-fixed_window+sentence_boundary | en | 0.6364 | 0.5076 | 0.5392 | 0.8571 | 1.0000 | 0.0000 |
| lexical-rerank-on-freshness-on-fixed_window+sentence_boundary | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| lexical-rerank-on-freshness-on-fixed_window+sentence_boundary | roman_urdu | 0.4545 | 0.3818 | 0.3988 | 0.6000 | 1.0000 | 0.1429 |
| lexical-rerank-on-freshness-on-fixed_window+sentence_boundary | overall | 0.3636 | 0.2965 | 0.3127 | 0.7500 | 1.0000 | 0.0870 |

## L16 graph-node eval rows

One row per graph node purpose. Populate from Lane E's handoff; do not invent effects.

| node | purpose | required_eval_row | measured_effect |
| --- | --- | --- | --- |
| route | Classify language, intent and metadata filters for a query. | Language + filter extraction exact-match on mini-golden.json; must not regress vs the linear baseline. | Measured: 36/36 records route to a supported language with a resolvable or intentionally empty filter; no linear-baseline regression observed. |
| filter | Apply extracted metadata filters to candidate chunks; never a graph branch. | Filter precision/recall on the crafted corpus; no golden query loses its expected doc_id. | Measured: 33/33 answerable records retain the expected doc_id after filtering. |
| search | Recall candidates with dense vectors plus in-domain lexical fusion. | recall@k and MRR vs dense-only; lexical-only uses an injected domain-local ChunkSource for full-corpus recall. | Measured hybrid-vs-dense recall@5 delta (rerank off): en +0.1818, ur +0.0000, roman_urdu +0.1818, overall +0.1212 |
| rerank | Reorder candidates through the injected Reranker port. | nDCG@10 and MRR delta against the rerank-off ablation. | Measured rerank-on minus rerank-off (hybrid) ndcg: en -0.1387, ur +0.0000, roman_urdu +0.0000, overall -0.0462. No measured gain on this corpus. |
| abstain | Emit an explicit, citation-free abstention with a next step when evidence is weak. | Abstention precision on the weak-evidence fixture; zero fabricated facts. | Measured abstention precision 0.0769 overall; the three fee rows abstain with no cited facts. |
| answer | Synthesize a cited answer whose data block is delimited and labelled. | Faithfulness and citation-resolution rate on mini-golden.json. | Measured faithfulness 0.6667 and citation-resolution 1.0000 overall (hybrid, rerank on), read natively from Citation.last_crawled. |
| retry_rewrite | Rewrite a weakly retrieved query once and repeat the search (capped loop). | recall@k gain on weak-evidence rows vs the single-pass baseline. | Removed after E3 (node deleted per L16 zero-gain verdict); retry_rewrite_enabled / retry_rewrite_iterations retained as dormant flags; reversal requires the parked live-transport re-run. |
| clarify | Ask the student for a missing required filter instead of guessing. | Clarification precision after filter-extraction errors; no needless clarifications. | Removed after E5 (node deleted per L16 zero-gain verdict; weak-row recall@5 en 7 / ur 11 / roman_urdu 6, n=24 incl. 6 feedback-derived rows = +0.000000 on en/ur/roman_urdu/overall); no substitute node added. Reversal requires the parked live-transport re-run showing a gain on this node's row (live transport supplying a parsed missing filter, CLARIFY_DOC_ID). |
| multihop | Answer a question that must reference evidence from a second document. | Faithfulness on a two-document multi-hop fixture. | Removed after E5 (node deleted per L16 zero-gain verdict; weak-row recall@5 en 7 / ur 11 / roman_urdu 6, n=24 incl. 6 feedback-derived rows = +0.000000 on en/ur/roman_urdu/overall); no substitute node added. Reversal requires the parked live-transport re-run showing a gain on this node's row (live transport supplying a second-document query, MULTIHOP_QUERY). |
| checkpoint_followup | Carry prior turns and citations into a checkpointed follow-up. | Citation continuity and faithfulness on a follow-up fixture. | Removed after E5 (node deleted per L16 zero-gain verdict; weak-row recall@5 en 7 / ur 11 / roman_urdu 6, n=24 incl. 6 feedback-derived rows = +0.000000 on en/ur/roman_urdu/overall); no substitute node added. Reversal requires the parked live-transport re-run showing a gain on this node's row (live transport supplying carried citation ids, FOLLOWUP_CITATIONS). LangGraph dependency stays CLOSED as not adopted. |

---

# Ablation: hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary

- backend: `fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory|feedback=derived|feedback_source=fixture-transcript|live_feedback=False`
- ADR-0010 strip: `labelled in-memory boundary strip (D2 not merged)`
- corpus: `fixture-corpus-v1-integrated`
- golden set: `curated-30-plus-feedback-6-v1`
- variant: `hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary` (chunking: `fixed_window+sentence_boundary`)
- clock: `FakeClock(2026-01-01T00:00:00+00:00)`
- top_k (k): `5`
- feedback input: labelled offline fixture transcript, NOT live user feedback (ADR 0009).
- timestamp: `2026-01-01T00:00:00+00:00`
- config fingerprint: `e5afd8874c69158b03b8e703fd85be27a9d74efc804a8d8cf4a819313e84c19d`
- scoring: retrieval metrics pool answerable ground truth; faithfulness and citation-resolution pool answered records; abstention precision pools all records.
- first integrated-pipeline run; adapters are real but offline, no live provider or network call; a zero row is a measured result (L1).

| language | n_questions | n_answerable | n_answered | recall@5 | mrr | ndcg | faithfulness | citation_resolution | abstention_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| en | 12 | 11 | 4 | 0.3636 | 0.2273 | 0.2601 | 0.7500 | 1.0000 | 0.0000 |
| ur | 12 | 11 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0833 |
| roman_urdu | 12 | 11 | 5 | 0.4545 | 0.3864 | 0.4028 | 0.6000 | 1.0000 | 0.1429 |
| overall | 36 | 33 | 9 | 0.2727 | 0.2045 | 0.2210 | 0.6667 | 1.0000 | 0.0769 |
