"""Regression gate: committed thresholds, fail/pass behaviour, CI marker (L1/L11)."""

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
PINNED_BASELINE_SHA256 = "8a8c6aea75a19d8c0887ecce1247e24fb4e7c0c378b26cff5c5783e6230baa5d"


def _result() -> Any:
    golden = load_golden_set(
        json.loads((ROOT / "eval/golden/golden.json").read_text(encoding="utf-8"))
    )
    registry = load_fixture_registry(
        json.loads((ROOT / "eval/golden/fixture-registry.json").read_text(encoding="utf-8"))
    )
    return run_variant(golden, registry, DEFAULT_VARIANT, top_k=5)


def _normalized_baseline_bytes() -> bytes:
    return BASELINE_PATH.read_bytes().replace(b"\r\n", b"\n")


def test_baseline_file_is_committed_and_unchanged() -> None:
    assert hashlib.sha256(_normalized_baseline_bytes()).hexdigest() == PINNED_BASELINE_SHA256
    baseline = load_baseline(BASELINE_PATH)
    assert baseline.baseline_id == "mechanics-validation-fake-v1"
    assert baseline.backend == "fake"
    assert set(baseline.thresholds) == {"en", "ur", "roman_urdu", "overall"}


def test_gate_fails_when_a_metric_drops_below_the_committed_baseline() -> None:
    result = _result()
    baseline = load_baseline(BASELINE_PATH)
    regressed = replace(
        result, overall=replace(result.overall, recall_at_k=result.overall.recall_at_k - 0.01)
    )
    with pytest.raises(RegressionError, match="regressed") as exc:
        assert_no_regression(regressed, baseline)
    assert any("overall.recall_at_k" in failure for failure in exc.value.context["failures"])


def test_gate_passes_when_metrics_hold_and_fails_on_label_mismatch() -> None:
    result = _result()
    baseline = load_baseline(BASELINE_PATH)
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
def test_committed_gate_passes_on_the_labelled_fake_baseline() -> None:
    result = _result()
    baseline = load_baseline(BASELINE_PATH)
    assert assert_no_regression(result, baseline).passed
    assert "fake" in baseline.note and "Mechanics validation" in baseline.note
    assert isinstance(baseline, Baseline)
