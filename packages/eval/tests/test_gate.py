"""Regression gate: committed thresholds, fail/pass behaviour, CI marker (L1/L11).

The committed baseline is the first integrated-pipeline run. CI's local gate
self-test uses an independently pinned fake-backend baseline (the milestone-1
mechanics numbers); no threshold is relaxed to make either pass.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from uni_rag_core.errors import ValidationError
from uni_rag_eval.domain.golden import load_fixture_registry, load_golden_set
from uni_rag_eval.domain.variant import DEFAULT_VARIANT
from uni_rag_eval.runner.gate import (
    Baseline,
    RegressionError,
    assert_no_regression,
    compare_to_baseline,
    load_baseline,
)
from uni_rag_eval.service.run import run_variant

ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = ROOT / "eval/golden/baseline.json"
PINNED_BASELINE_SHA256 = "0a4ab373a255f085063949c7fcc62ec4f75c06f5205eebfb1703ed7177049813"
_METRICS = (
    "recall_at_k",
    "mrr",
    "ndcg",
    "faithfulness",
    "citation_resolution",
    "abstention_precision",
)


def _result() -> Any:
    golden = load_golden_set(
        json.loads((ROOT / "eval/golden/golden.json").read_text(encoding="utf-8"))
    )
    registry = load_fixture_registry(
        json.loads((ROOT / "eval/golden/fixture-registry.json").read_text(encoding="utf-8"))
    )
    return run_variant(golden, registry, DEFAULT_VARIANT, top_k=5)


# Independently pinned fake-backend mechanics numbers (the milestone-1 baseline,
# kept verbatim here as a test oracle). Not derived from the result under test,
# so the gate self-test can actually fail on a regression.
_FAKE_THRESHOLDS: dict[str, dict[str, float]] = {
    "en": {
        "recall_at_k": 0.6666666666666666,
        "mrr": 0.5555555555555556,
        "ndcg": 0.5846510563492129,
        "faithfulness": 0.8333333333333334,
        "citation_resolution": 1.0,
        "abstention_precision": 0.0,
    },
    "ur": {
        "recall_at_k": 0.0,
        "mrr": 0.0,
        "ndcg": 0.0,
        "faithfulness": 0.0,
        "citation_resolution": 0.0,
        "abstention_precision": 0.1,
    },
    "roman_urdu": {
        "recall_at_k": 0.4444444444444444,
        "mrr": 0.4444444444444444,
        "ndcg": 0.4444444444444444,
        "faithfulness": 0.5,
        "citation_resolution": 1.0,
        "abstention_precision": 0.16666666666666666,
    },
    "overall": {
        "recall_at_k": 0.37037037037037035,
        "mrr": 0.3333333333333333,
        "ndcg": 0.34303183359788575,
        "faithfulness": 0.7,
        "citation_resolution": 1.0,
        "abstention_precision": 0.10526315789473684,
    },
}


def _fake_baseline() -> Baseline:
    """Independently pinned deterministic fake baseline for the gate self-test."""
    result = _result()
    return Baseline(
        baseline_id="local-fake-gate-selftest",
        backend="fake",
        corpus=result.context.corpus,
        golden_id=result.context.golden_id,
        variant_name=result.context.variant_name,
        top_k=result.context.top_k,
        note="Deterministic fake-backend baseline for gate self-test; not a quality claim.",
        thresholds={language: dict(values) for language, values in _FAKE_THRESHOLDS.items()},
    )


def _normalized_baseline_bytes() -> bytes:
    return BASELINE_PATH.read_bytes().replace(b"\r\n", b"\n")


def test_baseline_file_is_committed_and_unchanged() -> None:
    assert hashlib.sha256(_normalized_baseline_bytes()).hexdigest() == PINNED_BASELINE_SHA256
    baseline = load_baseline(BASELINE_PATH)
    assert baseline.baseline_id == "integrated-offline-v1"
    assert "google_genai" in baseline.backend and "live=False" in baseline.backend
    assert baseline.corpus == "fixture-corpus-v1-integrated"
    assert set(baseline.thresholds) == {"en", "ur", "roman_urdu", "overall"}
    assert set(next(iter(baseline.thresholds.values()))) == set(_METRICS)


def test_committed_baseline_documents_the_integrated_backend_and_threshold_change() -> None:
    baseline = load_baseline(BASELINE_PATH)
    assert "integrated-pipeline" in baseline.note
    assert "no live provider" in baseline.note
    assert "not a silent threshold relaxation" in baseline.note


def test_gate_fails_when_a_metric_drops_below_the_committed_baseline() -> None:
    result = _result()
    baseline = _fake_baseline()
    regressed = replace(
        result, overall=replace(result.overall, recall_at_k=result.overall.recall_at_k - 0.01)
    )
    with pytest.raises(RegressionError, match="regressed") as exc:
        assert_no_regression(regressed, baseline)
    assert any("overall.recall_at_k" in failure for failure in exc.value.context["failures"])


def test_gate_passes_when_metrics_hold_and_fails_on_label_mismatch() -> None:
    result = _result()
    baseline = _fake_baseline()
    assert assert_no_regression(result, baseline).passed
    mismatched = replace(result, context=replace(result.context, backend="real"))
    report = compare_to_baseline(mismatched, baseline)
    assert not report.passed
    assert any("label backend" in failure for failure in report.failures)


def test_threshold_changes_are_detected_instead_of_silently_relaxing() -> None:
    original = _normalized_baseline_bytes()
    payload = json.loads(original)
    payload["thresholds"]["overall"]["recall_at_k"] = 0.0
    mutated = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert hashlib.sha256(mutated).hexdigest() != hashlib.sha256(original).hexdigest()
    with pytest.raises(ValidationError):
        load_baseline(ROOT / "eval/golden/does-not-exist.json")


@pytest.mark.parametrize(
    ("mutate", "expected_message"),
    [
        (lambda data: data["thresholds"]["overall"].update(recall_at_k=float("nan")), "non-finite"),
        (lambda data: data["thresholds"].pop("ur"), "every language"),
        (
            lambda data: data["thresholds"]["overall"].pop("mrr"),
            "every metric",
        ),
        (
            lambda data: data["thresholds"]["overall"].update(mrr=-1.0),
            "out of range",
        ),
    ],
)
def test_baseline_cannot_disable_a_gate_through_nan_or_omission(
    tmp_path: Path, mutate: Any, expected_message: str
) -> None:
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    mutate(payload)
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValidationError, match=expected_message):
        load_baseline(path)


def test_comparison_boundary_rejects_an_incomplete_baseline() -> None:
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    payload["thresholds"].pop("ur")
    incomplete = Baseline.model_validate(payload)
    with pytest.raises(ValidationError, match="every language"):
        compare_to_baseline(_result(), incomplete)


@pytest.mark.gate
def test_committed_gate_passes_on_the_labelled_local_baseline() -> None:
    result = _result()
    assert assert_no_regression(result, _fake_baseline()).passed
    baseline = load_baseline(BASELINE_PATH)
    assert hashlib.sha256(_normalized_baseline_bytes()).hexdigest() == PINNED_BASELINE_SHA256
    assert "integrated-pipeline" in baseline.note
