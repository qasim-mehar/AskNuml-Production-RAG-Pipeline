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
  handoff; the six linear stages are measured from the ablation, and the four future
  control-flow nodes stay `awaiting measurement` (L16).

## Gate

`uv run python -m uni_rag_eval.runner.gate` exits non-zero on any regression or label
mismatch. The committed baseline is an integrated run, so the CLI needs the retrieval
callable handed in by configuration: pass
`--pipeline-factory module:attr --backend <label> --corpus <label> --clock <label>`.
Without a factory the CLI refuses to compare a local fake run against an integrated
baseline (exit 2) rather than report a misleading regression. The fake-backend self-test
runs in pytest via `uv run pytest -m gate packages/eval/tests` (used by CI/`make gate`).
