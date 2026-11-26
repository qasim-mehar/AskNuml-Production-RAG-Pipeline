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
- `golden/feedback-fixture.json` — hand-written, transcript-shaped feedback rows with
  `live_feedback: false`. These are fixtures, **not** real user feedback: ADR 0009's route
  persists nothing and real feedback ingestion stays parked.
- `golden/golden-feedback.json` — the extended golden set (30 curated + 6 feedback-derived
  rows, 12 per language). Every derived row carries the label
  `feedback-derived|source=fixture-transcript|live_feedback=False`; expected chunk ids
  resolve against the fixture corpus, so none dangles.
- `golden/baseline-feedback.json` — a **separate, labelled baseline extension** for the
  extended golden set. `golden/baseline.json` stays byte-identical (blob `c1e52839bf…`);
  divergences are reported in `reports/feedback-reconciliation.md`, never absorbed.
- `reports/` — generated tables, gitignored except `reports/latest.md` (the committed
  latest summary plus default-variant table). The runner regenerates one markdown + CSV
  table per variant with `uv run python -m uni_rag_eval.service.run`. Without
  `--pipeline-factory` that CLI regenerates **fake-backend** tables; to reproduce the
  committed integrated tables, hand in the composition with `--pipeline-factory
  module:attr --backend <label> --corpus <label> --clock <label>` (same flags as the gate).
  Only a fully labelled composition (`--pipeline-factory` plus `--backend`) rewrites the
  committed `latest.md`; a plain fake run cannot silently replace the integrated summary.
  `--feedback <fixture>` ingests a labelled offline transcript and enforces the provenance
  suffix on the backend label; `--write-golden` and `--write-baseline` emit the extended
  golden set and a separate labelled baseline extension (never `baseline.json`).
- `reports/summary.md` — includes the L16 graph-node table. Its rows come from Lane E's
  handoff; the six linear stages are measured from the ablation. The `retry_rewrite` row
  moved from measured to **removed** in E3 (node deleted per the zero-gain verdict; the
  flags stay dormant; reversal requires the parked live-transport re-run). F5 measured
  the three remaining control-flow nodes (`clarify`, `multihop`, `checkpoint_followup`);
  all three rows moved from `awaiting measurement` to measured zero-gain `REMOVE`
  verdicts, so Lane E needs removal prompts next milestone (L16).
- `reports/retry-rewrite-comparison.md` / `.csv` — the historical F3 measurement of
  recall@5 on the weak-evidence subset with `retry_rewrite_enabled` off (single pass) and
  on (cap 1), per language and overall, with the KEEP/REMOVE verdict. E3 removed the node;
  this pair is a retained measurement, not an actively measured node.
- `reports/strategy-comparison.md` / `.csv` — the chunking ablation rerun with two corpora:
  the same fixture documents indexed once under `fixed_window` and once under
  `sentence_boundary`, each queried against its own corpus. Golden ids are translated
  into each corpus, so no reference dangles (L12). A tie is reported as measured (L1).
- `composition.py` — the run-only pipeline factory handed in by configuration. It lives in
  `eval/` (not in the shipped `uni_rag_eval` package, which imports only `uni_rag_core`).
  It composes Lane E's public `RetrievalPipeline` from core ports with real offline
  adapters, passes the dormant `retry_rewrite` flags retained after E3's removal
  (no node is live), and applies the labelled **in-memory**
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

To regenerate the F4 extended-golden tables and its declared baseline extension (L4):

```
uv run python -m uni_rag_eval.service.run \
  --golden eval/golden/golden-feedback.json \
  --feedback eval/golden/feedback-fixture.json \
  --pipeline-factory eval.composition:build_pipeline \
  --backend 'fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory|feedback=derived|feedback_source=fixture-transcript|live_feedback=False' \
  --corpus fixture-corpus-v1-integrated \
  --clock 'FakeClock(2026-01-01T00:00:00+00:00)' \
  --run-id integrated-offline-feedback-fixture-v1 \
  --write-baseline eval/golden/baseline-feedback.json
```

`--feedback` re-derives and validates the golden rows from the labelled fixture before the
run; the runner enforces the provenance suffix on the backend label (never live feedback).

To regenerate the F5 control-flow-node verdict tables (L1/L16):

```
uv run python -m uni_rag_eval.service.run --mode f5 \
  --golden eval/golden/golden-feedback.json \
  --feedback eval/golden/feedback-fixture.json \
  --pipeline-factory eval.composition:build_pipeline \
  --backend 'fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip|strip_source=in-memory|feedback=derived|feedback_source=fixture-transcript|live_feedback=False' \
  --corpus fixture-corpus-v1-integrated \
  --clock 'FakeClock(2026-01-01T00:00:00+00:00)' \
  --run-id integrated-offline-feedback-fixture-v1 \
  --baseline eval/golden/baseline-feedback.json
```

F5 runs one single pass and three node-on variants (the only difference is the
run-only `node_variant` axis in `eval/composition.py`; no production node is added).
The weak-evidence subset is an answerable row with single-pass confidence < 0.35.
Its **one declared rule** for the six feedback-derived rows is
`include-feedback-derived|source=fixture-transcript|live_feedback=False`: they are
included for every node because they are grounded in the fixture corpus and are
part of the operative extended golden set (`curated-30-plus-feedback-6-v1`) and
its labelled baseline extension. The rule is printed on every report and on all
three `latest.md` rows. `baseline.json` stays byte-identical (blob
`c1e52839bf…`); extended comparisons gate against `baseline-feedback.json` only.

- `reports/{clarify,multihop,checkpoint_followup}-comparison.{md,csv}` — per-language
  recall@5 on/off and gain, weak-row counts, the full label chain and the L16 verdict.
  All three measure `+0.000000` overall (n=24 weak rows: en 7, ur 11, roman_urdu 6),
  hence `REMOVE`. The node-prompt transports echo their prompts, so no missing filter,
  second-document query or carried citation is produced; reversal conditions are
  recorded on each report but not acted on. Live-provider re-runs stay parked (L1/L17).

## Gate

`uv run python -m uni_rag_eval.runner.gate` exits non-zero on any regression or label
mismatch. The committed baseline is an integrated run, so the CLI needs the retrieval
callable handed in by configuration: pass
`--pipeline-factory module:attr --backend <label> --corpus <label> --clock <label>`.
Without a factory the CLI refuses to compare a local fake run against an integrated
baseline (exit 2) rather than report a misleading regression. The fake-backend self-test
runs in pytest via `uv run pytest -m gate packages/eval/tests` (used by CI/`make gate`).
