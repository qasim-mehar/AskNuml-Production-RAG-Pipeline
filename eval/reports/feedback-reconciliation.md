# Feedback-to-golden reconciliation — F4 (offline fixture transcript)

- Campaign: `pipeline-mvp`
- Branch: `lane/f-eval-m4` from PIN `e1d37093388378cf659eda9efa8189379fed3e5b` (isolated worktree).
- Curated golden set: `curated-30-v1` (30 rows). Extended set: `curated-30-plus-feedback-6-v1` (36 rows).
- Corpus: `fixture-corpus-v1-integrated`; clock: `FakeClock(2026-01-01T00:00:00+00:00)`; `top_k=5`.
- Backend (both runs): labelled real-offline adapters with the ADR-0010 in-memory strip; the
  F4 run appends `|feedback=derived|feedback_source=fixture-transcript|live_feedback=False`.

## Honest input statement

H2's `POST /api/v1/feedback` route is live but **persists nothing** (ADR 0009, parking lot:
"feedback auth/persistence"). There is no real feedback event stream to read. The only input
ingested here is `eval/golden/feedback-fixture.json`: hand-written, transcript-shaped rows
with `source: "fixture-transcript"` and `live_feedback: false`. No report, label or golden row
claims live user feedback is flowing; real feedback ingestion stays **PARKED**.

## Extended-golden inventory

| language | curated rows | feedback-derived rows added | extended rows | provenance label on derived rows |
| --- | --- | --- | --- | --- |
| en | 10 | 2 (`g-fb-en-01`, `g-fb-en-02`) | 12 | `feedback-derived|source=fixture-transcript|live_feedback=False` |
| ur | 10 | 2 (`g-fb-ur-01`, `g-fb-ur-02`) | 12 | `feedback-derived|source=fixture-transcript|live_feedback=False` |
| roman_urdu | 10 | 2 (`g-fb-ru-01`, `g-fb-ru-02`) | 12 | `feedback-derived|source=fixture-transcript|live_feedback=False` |
| overall | 30 | 6 | 36 | same label on all 6 derived rows |

Each derived row carries the question, `expected_filters`, `expected_chunk_ids` (expected
evidence), `expected_answer_gist`, abstention shape and the provenance label. All 36 golden
references resolve against the fixture corpus; translating into either per-strategy corpus
also leaves zero dangling ids (the F3 guarantee). Curated rows keep `provenance = null`.

## Baseline extension decision

The extended run has a different `golden_id`, so gating it against `baseline.json` would fail
on labels by design. Rather than silently change the committed thresholds:

- `eval/golden/baseline.json` is **byte-identical** — git blob
  `c1e52839bf9064b8eb465356f8c74927697a8536` (sha256
  `0a4ab373a255f085063949c7fcc62ec4f75c06f5205eebfb1703ed7177049813`). No value, note or
  label was edited; `packages/eval/tests/test_gate.py` keeps its pin.
- `eval/golden/baseline-feedback.json` is a **separate, labelled extension**
  (`baseline_id: integrated-offline-feedback-fixture-v1`) carrying the measured thresholds for
  the extended golden set and the feedback-fixture backend label. It is a declared artifact,
  not a replacement: the gate still compares the curated run to `baseline.json`.

## Divergence — REPORTED, never absorbed

Curated baseline thresholds → extended-set measured values (delta):

| language | recall@5 | mrr | ndcg | faithfulness | citation_resolution | abstention_precision |
| --- | --- | --- | --- | --- | --- | --- |
| en | 0.4444 → 0.3636 (-0.0808) | 0.2778 → 0.2273 (-0.0505) | 0.3179 → 0.2601 (-0.0578) | 0.7500 → 0.7500 (+0.0000) | 1.0000 → 1.0000 (+0.0000) | 0.0000 → 0.0000 (+0.0000) |
| ur | 0.0000 → 0.0000 (+0.0000) | 0.0000 → 0.0000 (+0.0000) | 0.0000 → 0.0000 (+0.0000) | 0.0000 → 0.0000 (+0.0000) | 0.0000 → 0.0000 (+0.0000) | 0.1000 → 0.0833 (-0.0167) |
| roman_urdu | 0.5556 → 0.4545 (-0.1010) | 0.4722 → 0.3864 (-0.0859) | 0.4923 → 0.4028 (-0.0895) | 0.6000 → 0.6000 (+0.0000) | 1.0000 → 1.0000 (+0.0000) | 0.2000 → 0.1429 (-0.0571) |
| overall | 0.3333 → 0.2727 (-0.0606) | 0.2500 → 0.2045 (-0.0455) | 0.2701 → 0.2210 (-0.0491) | 0.6667 → 0.6667 (+0.0000) | 1.0000 → 1.0000 (+0.0000) | 0.1000 → 0.0769 (-0.0231) |

These are **different corpora of questions** (36 vs 30), not a regression of the same run:
retrieval metrics pool answerable ground truth, and abstention precision pools every record,
so both denominators change when six answerable rows are added. Faithfulness and
citation-resolution are unchanged because the answered-record subset and its evidence are
unchanged by the added rows. No threshold was loosened to hide the move; the deltas are
written down here under the same "reported, never absorbed" rule the integration lane used
in `integration-reconciliation.md`.

## Published tables

`eval/reports/` carries one `{md,csv}` pair per ablation variant, `summary.md` / `.csv`
(including the L16 node rows), and `latest.md` (committed summary + default-variant table).
All carry the feedback-fixture backend label and the extended golden id. No live provider
or network call was made in any run.

## Parked — recorded, not acted on

- Opt-in live-provider re-run of `retry_rewrite` (reversal of the L16 REMOVE verdict).
- Real feedback auth/persistence and real feedback-to-golden ingestion (ADR 0009, parking lot).
- Live-transport comparison of provider adapters; fakes/offline transports remain the default.
