# eval data

`golden/` holds curated, version-controlled golden question sets used as evaluation inputs.
`reports/` holds generated evaluation reports and scores; these are outputs, not source data.

## Files

- `golden/golden.json` — 30 curated questions: 10 English, 10 Urdu, 10 Roman Urdu.
  Every answerable record names chunk ids from `fixture-registry.json`; the three fee
  questions are expected abstentions because no fixture document states a fee.
- `golden/fixture-registry.json` — the fake backend's corpus. `source_path` values point
  at real files under `tests/fixtures/`; chunk texts are taken from those files (the
  PDF chunk is its complete text, `CS-101 Course Outline`). Source URLs and crawl dates
  are synthetic fixture metadata, not live provenance.
- `golden/baseline.json` — thresholds measured from the labelled fake-backend mechanics
  validation run at full precision. These numbers validate harness mechanics only;
  they are **not a quality claim**. Changing this file requires a Lane F handoff note;
  its sha256 is pinned by `packages/eval/tests/test_gate.py`.
- `reports/` — generated tables, gitignored except `reports/latest.md` (the committed
  latest summary plus default-variant table). The runner regenerates one markdown + CSV
  table per variant with `uv run python -m uni_rag_eval.service.run`.
- `reports/summary.md` — includes the L16 graph-node table, empty-and-waiting until
  Lane E supplies node purposes and required eval rows in its handoff.

## Gate

`uv run python -m uni_rag_eval.runner.gate` exits non-zero on any regression or label
mismatch. `uv run pytest -m gate packages/eval/tests` exposes the same check as a
pytest marker for CI (Lane 0 wires the Makefile/ci.yml invocation).
