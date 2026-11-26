"""Offline feedback-to-golden ingestion tests (L1/L5/L7/L11/L12).

The feedback route persists nothing (ADR 0009), so these tests pin the labelled
fixture-transcript path only. No test claims live feedback is flowing.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from uni_rag_core.errors import ValidationError
from uni_rag_eval.domain.feedback import (
    FEEDBACK_PROVENANCE,
    FEEDBACK_SOURCE,
    assert_offline_feedback_label,
    feedback_backend_label,
    feedback_derived_records,
    feedback_row_counts,
    ingest_feedback,
    load_feedback_fixture,
)
from uni_rag_eval.domain.golden import (
    chunks_for_strategy,
    chunks_from_registry,
    golden_for_strategy,
    load_fixture_registry,
    load_golden_set,
    validate_golden_set,
)
from uni_rag_eval.domain.variant import DEFAULT_VARIANT, FIXED_WINDOW, SENTENCE_BOUNDARY
from uni_rag_eval.runner.gate import load_baseline
from uni_rag_eval.runner.harness import language_counts
from uni_rag_eval.service.run import (
    main,
    measured_l16_rows,
    run_ablation_suite,
    run_variant,
    write_baseline_extension,
)

ROOT = Path(__file__).resolve().parents[3]
GOLDEN_DIR = ROOT / "eval/golden"
PINNED_BASELINE_BLOB = "c1e52839bf9064b8eb465356f8c74927697a8536"
PINNED_BASELINE_SHA256 = "0a4ab373a255f085063949c7fcc62ec4f75c06f5205eebfb1703ed7177049813"
EXTENDED_GOLDEN_ID = "curated-30-plus-feedback-6-v1"


def _read(name: str) -> Any:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


def _inputs() -> tuple[Any, Any, Any]:
    golden = load_golden_set(_read("golden.json"))
    registry = load_fixture_registry(_read("fixture-registry.json"))
    fixture = load_feedback_fixture(_read("feedback-fixture.json"))
    return golden, registry, fixture


def _verified(registry: Any) -> set[str]:
    return {doc.source_path for doc in registry.documents if (ROOT / doc.source_path).is_file()}


def _extended() -> Any:
    golden, registry, fixture = _inputs()
    return ingest_feedback(
        golden,
        fixture,
        registry,
        golden_id=EXTENDED_GOLDEN_ID,
        description=(
            "30 curated questions plus 6 labelled feedback-derived rows from the "
            "offline fixture transcript (2 per language). NOT real user feedback: "
            "the feedback route persists nothing (ADR 0009) and real ingestion is parked."
        ),
    )


def test_feedback_fixture_is_labelled_offline_fixture_transcript() -> None:
    _, _, fixture = _inputs()
    assert fixture.source == FEEDBACK_SOURCE
    assert fixture.live_feedback is False
    assert "NOT user feedback" in fixture.description
    assert len(fixture.rows) == 6
    assert feedback_row_counts(fixture) == {"en": 2, "ur": 2, "roman_urdu": 2}
    assert all(row.sentiment in {"positive", "negative"} for row in fixture.rows)
    assert all(row.answer_id and row.query for row in fixture.rows)


def test_ingestion_stamps_provenance_only_on_feedback_derived_rows() -> None:
    golden, _, _ = _inputs()
    extended = _extended()
    derived = feedback_derived_records(extended)
    assert len(derived) == 6
    assert all(record.provenance == FEEDBACK_PROVENANCE for record in derived)
    assert all("feedback-derived" in (record.provenance or "") for record in derived)
    assert all("live_feedback=False" in (record.provenance or "") for record in derived)
    assert all(record.provenance is None for record in extended.records[: len(golden.records)])
    assert extended.golden_id == EXTENDED_GOLDEN_ID
    assert "NOT real user feedback" in extended.description


def test_backend_labels_cannot_claim_live_feedback() -> None:
    base = "adapters=real-offline|live=False|ADR0010-strip|strip_source=in-memory"
    label = feedback_backend_label(base)
    assert label.startswith(base)
    assert f"feedback_source={FEEDBACK_SOURCE}" in label
    assert "feedback=derived" in label
    assert "live_feedback=False" in label
    assert feedback_backend_label(label) == label  # idempotent for configured labels
    partial = feedback_backend_label(f"{base}|feedback_source=fixture-transcript")
    assert "feedback=derived" in partial and "live_feedback=False" in partial
    assert assert_offline_feedback_label(base) == base
    for claim in ("live_feedback=True", "feedback=live", "feedback=real", "LIVE FEEDBACK"):
        with pytest.raises(ValidationError, match="must not claim live feedback"):
            assert_offline_feedback_label(f"{base}|{claim}")


def test_live_feedback_fixture_is_rejected() -> None:
    payload = _read("feedback-fixture.json")
    payload["live_feedback"] = True
    with pytest.raises(ValidationError, match="labelled offline fixture"):
        load_feedback_fixture(payload)
    other = deepcopy(payload)
    other["live_feedback"] = False
    other["source"] = "live-user-feedback"
    with pytest.raises(ValidationError, match="labelled offline fixture"):
        load_feedback_fixture(other)


def test_extended_golden_has_zero_dangling_ids_in_every_corpus() -> None:
    _, registry, _ = _inputs()
    extended = _extended()
    validate_golden_set(extended, registry, _verified(registry))
    indexed = {chunk.chunk_id for chunk in chunks_from_registry(registry)}
    referenced = {cid for record in extended.records for cid in record.expected_chunk_ids}
    assert referenced <= indexed
    for strategy in (FIXED_WINDOW, SENTENCE_BOUNDARY):
        translated = golden_for_strategy(extended, registry, strategy)
        strategy_ids = {chunk.chunk_id for chunk in chunks_for_strategy(registry, strategy)}
        translated_refs = {
            cid for record in translated.records for cid in record.expected_chunk_ids
        }
        assert translated_refs <= strategy_ids


def test_ingestion_rejects_dangling_duplicate_and_incoherent_rows() -> None:
    golden, registry, fixture = _inputs()
    kwargs = {"golden_id": EXTENDED_GOLDEN_ID, "description": "x"}

    def mutated(index: int, **changes: Any) -> Any:
        rows = list(fixture.rows)
        rows[index] = rows[index].model_copy(update=changes)
        return fixture.model_copy(update={"rows": rows})

    with pytest.raises(ValidationError, match="dangles"):
        ingest_feedback(
            golden, mutated(0, expected_chunk_ids=["doc-nope::c99"]), registry, **kwargs
        )
    with pytest.raises(ValidationError, match="Duplicate golden id"):
        ingest_feedback(golden, mutated(1, feedback_id="fb-en-01"), registry, **kwargs)
    with pytest.raises(ValidationError, match="abstain feedback row"):
        ingest_feedback(golden, mutated(0, expected_abstain=True), registry, **kwargs)
    with pytest.raises(ValidationError, match="disagrees"):
        ingest_feedback(
            golden, mutated(0, expected_filters={"doc_id": "doc-other"}), registry, **kwargs
        )


def test_extended_golden_row_counts_per_language() -> None:
    golden, _, _ = _inputs()
    extended = _extended()
    assert len(extended.records) == 36
    assert language_counts(extended) == {"en": 12, "ur": 12, "roman_urdu": 12}
    assert language_counts(golden) == {"en": 10, "ur": 10, "roman_urdu": 10}
    assert feedback_row_counts(load_feedback_fixture(_read("feedback-fixture.json"))) == {
        "en": 2,
        "ur": 2,
        "roman_urdu": 2,
    }


def test_committed_extended_golden_matches_a_fresh_ingestion() -> None:
    committed = load_golden_set(_read("golden-feedback.json"))
    fresh = _extended()
    assert committed.golden_id == fresh.golden_id == EXTENDED_GOLDEN_ID
    assert [record.id for record in committed.records] == [record.id for record in fresh.records]
    assert language_counts(committed) == {"en": 12, "ur": 12, "roman_urdu": 12}
    assert len(feedback_derived_records(committed)) == 6
    _, registry, fixture = _inputs()
    reingested = ingest_feedback(
        committed,
        fixture,
        registry,
        golden_id=EXTENDED_GOLDEN_ID,
        description=committed.description,
    )
    assert [record.id for record in reingested.records] == [
        record.id for record in committed.records
    ]
    assert len(reingested.records) == 36


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def test_committed_baseline_is_byte_identical_while_extension_is_separate() -> None:
    baseline_path = GOLDEN_DIR / "baseline.json"
    assert _git_blob_sha1(baseline_path) == PINNED_BASELINE_BLOB
    assert (
        hashlib.sha256(baseline_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        == PINNED_BASELINE_SHA256
    )
    committed = load_baseline(baseline_path)
    extension = load_baseline(GOLDEN_DIR / "baseline-feedback.json")
    assert committed.baseline_id == "integrated-offline-v1"
    assert committed.golden_id == "curated-30-v1"
    assert extension.baseline_id == "integrated-offline-feedback-fixture-v1"
    assert extension.golden_id == EXTENDED_GOLDEN_ID
    assert "NOT a change to baseline.json" in extension.note
    assert extension.backend != committed.backend
    assert "live_feedback=False" in extension.backend
    assert "feedback_source=fixture-transcript" in extension.backend


def test_cli_feedback_run_enforces_the_label_and_never_forces_latest(tmp_path: Path) -> None:
    code = main(
        [
            "--golden",
            str(GOLDEN_DIR / "golden.json"),
            "--registry",
            str(GOLDEN_DIR / "fixture-registry.json"),
            "--feedback",
            str(GOLDEN_DIR / "feedback-fixture.json"),
            "--reports",
            str(tmp_path),
        ]
    )
    assert code == 0
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "feedback_source=fixture-transcript" in summary
    assert "NOT live user feedback" in summary
    # An unlabelled fake-backend run must not replace the committed summary.
    assert not (tmp_path / "latest.md").exists()


def test_cli_refuses_an_unlabelled_baseline_extension(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="requires --pipeline-factory and --backend"):
        main(
            [
                "--golden",
                str(GOLDEN_DIR / "golden.json"),
                "--registry",
                str(GOLDEN_DIR / "fixture-registry.json"),
                "--reports",
                str(tmp_path),
                "--write-baseline",
                str(tmp_path / "baseline.json"),
            ]
        )


def test_baseline_extension_cannot_overwrite_the_committed_baseline() -> None:
    golden, registry, _ = _inputs()
    result = run_variant(golden, registry, DEFAULT_VARIANT)
    with pytest.raises(RuntimeError, match="must not overwrite baseline.json"):
        write_baseline_extension((result,), GOLDEN_DIR / "baseline.json", "bad")


def test_l16_filter_effect_uses_the_extended_answerable_denominator(tmp_path: Path) -> None:
    golden, registry, _ = _inputs()
    extended = _extended()
    results = run_ablation_suite(extended, registry, tmp_path)
    effects = {
        row.node_name: row.measured_effect for row in measured_l16_rows(extended, registry, results)
    }
    assert "33/33" in effects["filter"]
    assert "36" in effects["route"]


def test_feedback_fixture_evidence_never_invents_facts() -> None:
    _, registry, fixture = _inputs()
    texts = {chunk.chunk_id: chunk.text for doc in registry.documents for chunk in doc.chunks}
    for row in fixture.rows:
        assert row.expected_answer_gist.strip()
        if not row.expected_abstain:
            assert row.expected_chunk_ids
            evidence = " ".join(texts[cid] for cid in row.expected_chunk_ids)
            assert evidence
            assert "fixture" not in row.expected_answer_gist.lower()
