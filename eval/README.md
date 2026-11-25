# eval data

`golden/` holds curated, version-controlled golden question sets used as evaluation inputs.
`reports/` holds generated evaluation reports and scores; these are outputs, not source data.

## Files

- `golden/golden.json` — 30 curated questions: 10 English, 10 Urdu, 10 Roman Urdu.
  Every answerable record names chunk ids from `fixture-registry.json`; the three fee
  questions are expected abstentions because no fixture document states a fee.
- `golden/fixture-registry.json` — the corpus used by the integrated run. `source_path`
  values point at real files under `tests/fixtures/`; every chunk pins a `content_hash`
  validated against its text at load, so no golden reference can dangle against the
  chunk set the pipeline indexes. Source URLs and crawl dates are synthetic fixture
  metadata, not live provenance.
- `golden/baseline.json` — the first integrated-pipeline baseline (backend labels, clock,
  corpus and k recorded inline). Its `note` explains the change from the milestone-1
  fake-backend mechanics numbers; those fake numbers are not a quality claim and are
  never blended into the integrated tables. Changing this file requires a Lane F handoff
  note; its sha256 is pinned by `packages/eval/tests/test_gate.py`.
- `reports/` — generated tables, gitignored except `reports/latest.md` (the committed
  latest summary plus default-variant table). The runner regenerates one markdown + CSV
  table per variant with `uv run python -m uni_rag_eval.service.run`. Without
  `--pipeline-factory` that CLI regenerates **fake-backend** tables; to reproduce the
  committed integrated tables, hand in the composition with `--pipeline-factory
  module:attr --backend <label> --corpus <label> --clock <label>` (same flags as the gate).
- `reports/summary.md` — includes the L16 graph-node table. Its rows come from Lane E's
  handoff; the six linear stages are measured from the ablation. The `retry_rewrite` row
  is now measured in milestone 3 (see `reports/retry-rewrite-comparison.md`); the three
  remaining control-flow nodes stay `awaiting measurement` (L16).
- `reports/retry-rewrite-comparison.md` / `.csv` — the L16 row measurement: recall@5 on
  the weak-evidence subset with `retry_rewrite_enabled` off (single pass) and on (cap 1),
  per language and overall, with the pure KEEP/REMOVE verdict printed alongside its numbers.
- `reports/strategy-comparison.md` / `.csv` — the chunking ablation rerun with two corpora:
  the same fixture documents indexed once under `fixed_window` and once under
  `sentence_boundary`, each queried against its own corpus. Golden ids are translated
  into each corpus, so no reference dangles (L12). A tie is reported as measured (L1).
- `composition.py` — the run-only pipeline factory handed in by configuration. It lives in
  `eval/` (not in the shipped `uni_rag_eval` package, which imports only `uni_rag_core`).
  It composes Lane E's public `RetrievalPipeline` from core ports with real offline
  adapters, sets the injected `retry_rewrite` flag, and applies the labelled **in-memory**
  ADR-0010 strip because Lane D's boundary strip has not merged. The backend label ends
  in `ADR0010-strip|strip_source=in-memory`. No live provider or network call.

To regenerate the milestone-3 reports byte-identically (L4):

```
uv run python -m uni_rag_eval.service.run --mode m3 \
  --pipeline-factory eval.composition:build_pipeline \
  --backend 'fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory' \
  --corpus fixture-corpus-v1-integrated \
  --clock 'FakeClock(2026-01-01T00:00:00+00:00)'
```

## Gate

`uv run python -m uni_rag_eval.runner.gate` exits non-zero on any regression or label
mismatch. The committed baseline is an integrated run, so the CLI needs the retrieval
callable handed in by configuration: pass
`--pipeline-factory module:attr --backend <label> --corpus <label> --clock <label>`.
Without a factory the CLI refuses to compare a local fake run against an integrated
baseline (exit 2) rather than report a misleading regression. The fake-backend self-test
runs in pytest via `uv run pytest -m gate packages/eval/tests` (used by CI/`make gate`).
