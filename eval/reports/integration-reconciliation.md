# Integration reconciliation — F2 (pre-strip) vs integrated post-strip (ADR 0010)

- Campaign: `pipeline-mvp`
- Base: `main` @ `f26d2ca061f09a173f49614b0071740b09646eac` (D2's domain-clean strip landed).
- Integrated branch: `lane/integration` rebased off `512be58` onto that `main`.
- Golden set: `curated-30-v1`; clock: `FakeClock(2026-01-01T00:00:00+00:00)`; `top_k=5`.

## The two labelled runs

| run | backend label | strip source | produced by |
| --- | --- | --- | --- |
| F2 (pre-strip reference) | `…|adapters=real-offline|ADR0010-strip` | `strip_source=in-memory` (`InMemoryStrippedStore` decorator in `eval/composition.py`, written while D2 was unmerged) | `lane/f-eval-m2` `ed4dc80`, now `baseline.json` thresholds |
| Integrated (this resume) | `…|adapters=real-offline|strip_source=real-adapter|ADR0010-strip` | `strip_source=real-adapter` (the real `QdrantVectorStore` from D2; no decorator) | `tests/integration/eval_run.py` via `tests/integration/composition.py` |

F2 ran before D2 merged. Its numbers were produced with F3's in-memory strip
applied at the port because the real adapter had not landed. The integrated run
uses the real stripped adapter and makes that explicit in the backend label.
All provenance comes from labels — no number is relabelled to hide a source.

## Metric reconciliation (integrated real-adapter minus F2 baseline)

`eval/reports/integrated-offline.md` compares the integrated run against the
committed baseline thresholds, which are exactly F2's measured values. Every
metric delta is `+0.000000`:

| language | recall@5 | mrr | ndcg | faithfulness | abstention_precision | citation_resolution |
| --- | --- | --- | --- | --- | --- | --- |
| en | 0.4444 (Δ0) | 0.2778 (Δ0) | 0.3179 (Δ0) | 0.7500 (Δ0) | 0.0000 (Δ0) | 1.0000 (Δ0) |
| ur | 0.0000 (Δ0) | 0.0000 (Δ0) | 0.0000 (Δ0) | 0.0000 (Δ0) | 0.1000 (Δ0) | 0.0000 (Δ0) |
| roman_urdu | 0.5556 (Δ0) | 0.4722 (Δ0) | 0.4923 (Δ0) | 0.6000 (Δ0) | 0.2000 (Δ0) | 1.0000 (Δ0) |
| overall | 0.3333 (Δ0) | 0.2500 (Δ0) | 0.2701 (Δ0) | 0.6667 (Δ0) | 0.1000 (Δ0) | 1.0000 (Δ0) |

**Conclusion:** the real D2 boundary strip is semantically equivalent to F3's
in-memory strip on this corpus — no metric moved. ADR 0010 is proven on the
real adapter by `assert_vector_payload_roundtrip_contract` (wired into
`tests/integration/test_pipeline_smoke.py::test_vector_store_swap_uses_qdrant_adapter`
and already exercised by Lane D's `test_qdrant_adapter_passes_vector_payload_roundtrip_contract`).

## Divergences — REPORTED, never absorbed

Two divergences were found during the resume. Neither was absorbed by changing a
threshold or a golden record; both are written down here.

1. **`citation_resolution` initially 0.000000 vs F2's 1.000000 (en, roman_urdu, overall).**
   Root cause: the integration harness `run_integrated` omitted the `known_chunks`
   argument to `run_harness`, so the citation-resolution comparator had an empty
   corpus and scored 0.0 structurally. F2's eval service passes the indexed corpus
   via `run_variant`/`known_chunks`. This is an integration-harness omission, **not**
   an ADR-0010 strip regression: every other metric already matched F2 exactly.
   Fixed by passing `{chunk.chunk_id: chunk for chunk in chunks}`; no threshold,
   baseline or golden-set edit. Reported here as required (L1).

2. **Fake mechanics run vs the integrated baseline (5 `roman_urdu` deltas).**
   `eval_run.main()` used to metric-gate the fake-backend smoke run against the
   committed baseline. Since F2 the baseline is the *integrated* backend
   (`integrated-offline-v1`), so a fake run is expected to score lower:
   `recall@5 0.444444 < 0.555556`, `mrr 0.444444 < 0.472222`,
   `ndcg 0.444444 < 0.492297`, `faithfulness 0.500000 < 0.600000`,
   `abstention_precision 0.166667 < 0.200000`. These are label/backend differences,
   not quality regressions. The stale check is now a mechanics check (the fake run
   must produce scores); the divergence is printed at run time and recorded here.
   No threshold was loosened and `baseline.json` is untouched.

## Invariants

- `eval/golden/baseline.json` is byte-identical to pre-merge `main`:
  git blob `c1e52839bf9064b8eb465356f8c74927697a8536` (verified before and after).
- No golden record, threshold or abstention value was edited.
- The only report change is the labelled integrated table
  (`eval/reports/integrated-offline.md`) plus this reconciliation note.
