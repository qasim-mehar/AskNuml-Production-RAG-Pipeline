# Ablation summary

- variants: `12`
- backend: `fake`
- corpus: `fixture-corpus-v1`
- golden set: `curated-30-v1`
- top_k: `5`
- all numbers are mechanics validation on the fake backend, not a quality claim.

| variant | language | recall@5 | mrr | ndcg | faithfulness | abstention_precision |
| --- | --- | --- | --- | --- | --- | --- |
| dense-rerank-off-freshness-off-awaiting-lane-c | en | 1.0000 | 0.5278 | 0.6471 | 0.8889 | 0.0000 |
| dense-rerank-off-freshness-off-awaiting-lane-c | ur | 1.0000 | 0.3981 | 0.5470 | 0.1111 | 0.0000 |
| dense-rerank-off-freshness-off-awaiting-lane-c | roman_urdu | 1.0000 | 0.4611 | 0.5928 | 0.5556 | 0.0000 |
| dense-rerank-off-freshness-off-awaiting-lane-c | overall | 1.0000 | 0.4623 | 0.5956 | 0.5185 | 0.0000 |
| dense-rerank-off-freshness-on-awaiting-lane-c | en | 1.0000 | 0.5278 | 0.6471 | 0.8889 | 0.0000 |
| dense-rerank-off-freshness-on-awaiting-lane-c | ur | 1.0000 | 0.3981 | 0.5470 | 0.1111 | 0.0000 |
| dense-rerank-off-freshness-on-awaiting-lane-c | roman_urdu | 1.0000 | 0.4611 | 0.5928 | 0.5556 | 0.0000 |
| dense-rerank-off-freshness-on-awaiting-lane-c | overall | 1.0000 | 0.4623 | 0.5956 | 0.5185 | 0.0000 |
| dense-rerank-on-freshness-off-awaiting-lane-c | en | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| dense-rerank-on-freshness-off-awaiting-lane-c | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| dense-rerank-on-freshness-off-awaiting-lane-c | roman_urdu | 0.4444 | 0.4444 | 0.4444 | 0.5000 | 0.1667 |
| dense-rerank-on-freshness-off-awaiting-lane-c | overall | 0.3704 | 0.3333 | 0.3430 | 0.7000 | 0.1053 |
| dense-rerank-on-freshness-on-awaiting-lane-c | en | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| dense-rerank-on-freshness-on-awaiting-lane-c | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| dense-rerank-on-freshness-on-awaiting-lane-c | roman_urdu | 0.4444 | 0.4444 | 0.4444 | 0.5000 | 0.1667 |
| dense-rerank-on-freshness-on-awaiting-lane-c | overall | 0.3704 | 0.3333 | 0.3430 | 0.7000 | 0.1053 |
| hybrid-rerank-off-freshness-off-awaiting-lane-c | en | 1.0000 | 0.7407 | 0.8069 | 0.8889 | 0.0000 |
| hybrid-rerank-off-freshness-off-awaiting-lane-c | ur | 0.6667 | 0.2315 | 0.3402 | 0.0000 | 0.0000 |
| hybrid-rerank-off-freshness-off-awaiting-lane-c | roman_urdu | 0.8889 | 0.5315 | 0.6199 | 0.5000 | 0.0000 |
| hybrid-rerank-off-freshness-off-awaiting-lane-c | overall | 0.8519 | 0.5012 | 0.5890 | 0.5217 | 0.0000 |
| hybrid-rerank-off-freshness-on-awaiting-lane-c | en | 1.0000 | 0.7407 | 0.8069 | 0.8889 | 0.0000 |
| hybrid-rerank-off-freshness-on-awaiting-lane-c | ur | 0.6667 | 0.2315 | 0.3402 | 0.0000 | 0.0000 |
| hybrid-rerank-off-freshness-on-awaiting-lane-c | roman_urdu | 1.0000 | 0.6426 | 0.7310 | 0.5556 | 0.0000 |
| hybrid-rerank-off-freshness-on-awaiting-lane-c | overall | 0.8889 | 0.5383 | 0.6260 | 0.5417 | 0.0000 |
| hybrid-rerank-on-freshness-off-awaiting-lane-c | en | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| hybrid-rerank-on-freshness-off-awaiting-lane-c | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| hybrid-rerank-on-freshness-off-awaiting-lane-c | roman_urdu | 0.4444 | 0.4444 | 0.4444 | 0.5000 | 0.1667 |
| hybrid-rerank-on-freshness-off-awaiting-lane-c | overall | 0.3704 | 0.3333 | 0.3430 | 0.7000 | 0.1053 |
| hybrid-rerank-on-freshness-on-awaiting-lane-c | en | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| hybrid-rerank-on-freshness-on-awaiting-lane-c | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| hybrid-rerank-on-freshness-on-awaiting-lane-c | roman_urdu | 0.4444 | 0.4444 | 0.4444 | 0.5000 | 0.1667 |
| hybrid-rerank-on-freshness-on-awaiting-lane-c | overall | 0.3704 | 0.3333 | 0.3430 | 0.7000 | 0.1053 |
| lexical-rerank-off-freshness-off-awaiting-lane-c | en | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| lexical-rerank-off-freshness-off-awaiting-lane-c | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| lexical-rerank-off-freshness-off-awaiting-lane-c | roman_urdu | 0.4444 | 0.4444 | 0.4444 | 0.5000 | 0.1667 |
| lexical-rerank-off-freshness-off-awaiting-lane-c | overall | 0.3704 | 0.3333 | 0.3430 | 0.7000 | 0.1053 |
| lexical-rerank-off-freshness-on-awaiting-lane-c | en | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| lexical-rerank-off-freshness-on-awaiting-lane-c | ur | 0.1111 | 0.0370 | 0.0556 | 0.0000 | 0.0000 |
| lexical-rerank-off-freshness-on-awaiting-lane-c | roman_urdu | 0.5556 | 0.5000 | 0.5145 | 0.6000 | 0.0000 |
| lexical-rerank-off-freshness-on-awaiting-lane-c | overall | 0.4444 | 0.3642 | 0.3849 | 0.6667 | 0.0000 |
| lexical-rerank-on-freshness-off-awaiting-lane-c | en | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| lexical-rerank-on-freshness-off-awaiting-lane-c | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| lexical-rerank-on-freshness-off-awaiting-lane-c | roman_urdu | 0.4444 | 0.4444 | 0.4444 | 0.5000 | 0.1667 |
| lexical-rerank-on-freshness-off-awaiting-lane-c | overall | 0.3704 | 0.3333 | 0.3430 | 0.7000 | 0.1053 |
| lexical-rerank-on-freshness-on-awaiting-lane-c | en | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| lexical-rerank-on-freshness-on-awaiting-lane-c | ur | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| lexical-rerank-on-freshness-on-awaiting-lane-c | roman_urdu | 0.4444 | 0.4444 | 0.4444 | 0.5000 | 0.1667 |
| lexical-rerank-on-freshness-on-awaiting-lane-c | overall | 0.3704 | 0.3333 | 0.3430 | 0.7000 | 0.1053 |

## L16 graph-node eval rows

One row per graph node purpose. Populate from Lane E's handoff; do not invent effects.

| node | purpose | required_eval_row | measured_effect |
| --- | --- | --- | --- |
| _awaiting Lane E handoff_ | node purposes pending | eval rows pending | not measured |

---

# Ablation: hybrid-rerank-on-freshness-off-awaiting-lane-c

- backend: `fake`
- corpus: `fixture-corpus-v1`
- golden set: `curated-30-v1`
- variant: `hybrid-rerank-on-freshness-off-awaiting-lane-c` (chunking: `awaiting-lane-c`)
- top_k: `5`
- timestamp: `2026-01-01T00:00:00+00:00`
- config fingerprint: `d8849a8a1c0843b4e4120fa2b85ed4727b82ab86910e755502cbc19978a04003`
- scoring: retrieval metrics pool answerable ground truth; faithfulness pools answered records; abstention precision pools all records.
- mechanics validation on a fake backend only; a zero row is a measured fake result, not a quality verdict.

| language | n_questions | n_answerable | n_answered | recall@5 | mrr | ndcg | faithfulness | abstention_precision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| en | 10 | 9 | 6 | 0.6667 | 0.5556 | 0.5847 | 0.8333 | 0.0000 |
| ur | 10 | 9 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1000 |
| roman_urdu | 10 | 9 | 4 | 0.4444 | 0.4444 | 0.4444 | 0.5000 | 0.1667 |
| overall | 30 | 27 | 10 | 0.3704 | 0.3333 | 0.3430 | 0.7000 | 0.1053 |
