"""Regression gate against a committed baseline (L1/L11).

Thresholds are *measured* values from a labelled mechanics-validation run. This
module never relaxes them: a run passes only when every metric is at or above
its committed threshold and its labels match the baseline's labels.
"""

from __future__ import annotations

import argparse
import importlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from uni_rag_core import UniRagError, ValidationError, get_logger
from uni_rag_eval.domain.golden import REQUIRED_LANGUAGES
from uni_rag_eval.runner.harness import MetricScores, RunContext, RunResult

_LOG = get_logger("uni_rag_eval.gate")
_METRIC_FIELDS: tuple[str, ...] = (
    "recall_at_k",
    "mrr",
    "ndcg",
    "faithfulness",
    "citation_resolution",
    "abstention_precision",
)


class RegressionError(UniRagError):
    """A run regressed against the committed baseline (L11)."""


class Baseline(BaseModel):
    """Committed thresholds and the labels of the run that produced them."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    baseline_id: str
    backend: str
    corpus: str
    golden_id: str
    variant_name: str
    top_k: int
    note: str
    thresholds: dict[str, dict[str, float]]


@dataclass(frozen=True)
class GateReport:
    """Failures found by the gate; empty failures means the gate passed."""

    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        """Return whether no regression was detected."""
        return not self.failures


def _reject_non_finite(constant: str) -> None:
    raise ValidationError("Baseline contains a non-finite number", context={"constant": constant})


def _validate_baseline(baseline: Baseline) -> Baseline:
    """Refuse incomplete or out-of-range thresholds: omissions must not disable the gate."""
    expected_languages = {language.value for language in REQUIRED_LANGUAGES} | {"overall"}
    if set(baseline.thresholds) != expected_languages:
        raise ValidationError(
            "Baseline must threshold every language and overall",
            context={"expected": sorted(expected_languages), "actual": sorted(baseline.thresholds)},
        )
    for language, thresholds in baseline.thresholds.items():
        if set(thresholds) != set(_METRIC_FIELDS):
            raise ValidationError(
                "Baseline must threshold every metric",
                context={"language": language, "actual": sorted(thresholds)},
            )
        for metric, value in thresholds.items():
            if not 0.0 <= value <= 1.0:
                raise ValidationError(
                    "Baseline threshold out of range",
                    context={"language": language, "metric": metric, "value": value},
                )
    return baseline


def load_baseline(path: Path) -> Baseline:
    """Load and parse the committed baseline file, raising a typed error if invalid."""
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError("Cannot read the baseline file", context={"path": str(path)}) from exc
    try:
        parsed = json.loads(payload, parse_constant=_reject_non_finite)
        return _validate_baseline(Baseline.model_validate(parsed))
    except (ValueError, PydanticValidationError) as exc:
        raise ValidationError("Invalid baseline file", context={"path": str(path)}) from exc


def _label_failures(context: RunContext, baseline: Baseline) -> list[str]:
    expected = {
        "backend": baseline.backend,
        "corpus": baseline.corpus,
        "golden_id": baseline.golden_id,
        "variant_name": baseline.variant_name,
        "top_k": baseline.top_k,
    }
    actual = {
        "backend": context.backend,
        "corpus": context.corpus,
        "golden_id": context.golden_id,
        "variant_name": context.variant_name,
        "top_k": context.top_k,
    }
    return [
        f"label {key}: baseline={expected[key]!r} run={actual[key]!r}"
        for key in sorted(expected)
        if actual[key] != expected[key]
    ]


def compare_to_baseline(result: RunResult, baseline: Baseline) -> GateReport:
    """Return every metric regression and label mismatch; no threshold is adjusted."""
    _validate_baseline(baseline)
    failures = _label_failures(result.context, baseline)
    scores: Mapping[str, MetricScores] = {
        **result.scores_by_language,
        "overall": result.overall,
    }
    for language, thresholds in sorted(baseline.thresholds.items()):
        if language not in scores:
            failures.append(f"{language}: missing from run")
            continue
        for metric in sorted(thresholds):
            if metric not in _METRIC_FIELDS:
                failures.append(f"{language}.{metric}: unknown metric in baseline")
                continue
            actual_value = getattr(scores[language], metric)
            threshold = thresholds[metric]
            if actual_value < threshold:
                failures.append(
                    f"{language}.{metric}: {actual_value:.6f} < baseline {threshold:.6f}"
                )
    return GateReport(failures=tuple(failures))


def assert_no_regression(result: RunResult, baseline: Baseline) -> GateReport:
    """Raise :class:`RegressionError` on any regression, otherwise return the report."""
    report = compare_to_baseline(result, baseline)
    if not report.passed:
        raise RegressionError(
            "Evaluation regressed against the committed baseline",
            context={"failures": list(report.failures), "baseline_id": baseline.baseline_id},
        )
    return report


def write_baseline_from_run(
    result: RunResult, path: Path, *, baseline_id: str, note: str
) -> Baseline:
    """Commit measured values as thresholds; call only after reviewing the run."""
    scores: dict[str, MetricScores] = {
        **result.scores_by_language,
        "overall": result.overall,
    }
    baseline = _validate_baseline(
        Baseline(
            baseline_id=baseline_id,
            backend=result.context.backend,
            corpus=result.context.corpus,
            golden_id=result.context.golden_id,
            variant_name=result.context.variant_name,
            top_k=result.context.top_k,
            note=note,
            # Full precision: rounding thresholds up would fail an unchanged run.
            thresholds={
                language: {
                    field: float(getattr(scores[language], field)) for field in _METRIC_FIELDS
                }
                for language in sorted(scores)
            },
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                baseline.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False
            )
        )
        handle.write("\n")
    return baseline


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run the default fake variant and gate it; return an exit code."""
    parser = argparse.ArgumentParser(description="Run the committed regression gate")
    parser.add_argument("--golden", type=Path, default=Path("eval/golden/golden.json"))
    parser.add_argument("--registry", type=Path, default=Path("eval/golden/fixture-registry.json"))
    parser.add_argument("--baseline", type=Path, default=Path("eval/golden/baseline.json"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--pipeline-factory",
        default=None,
        help="module:attr callable handed in by the integration configuration; "
        "returns a Query->Answer callable for one Variant (L3).",
    )
    parser.add_argument("--backend", default=None, help="label of the injected backend")
    parser.add_argument("--corpus", default=None, help="label of the injected corpus")
    parser.add_argument("--clock", default=None, help="label of the injected clock")
    args = parser.parse_args(argv)

    from uni_rag_eval.domain.variant import DEFAULT_VARIANT
    from uni_rag_eval.service.run import load_eval_inputs, run_variant

    golden, registry = load_eval_inputs(args.golden, args.registry)
    baseline = load_baseline(args.baseline)

    factory = None
    if args.pipeline_factory:
        module_name, separator, attr = args.pipeline_factory.partition(":")
        if not separator or not module_name or not attr:
            _LOG.error("eval.gate.config", reason="--pipeline-factory must be module:attr")
            return 2
        factory = getattr(importlib.import_module(module_name), attr)
    elif baseline.backend != "fake":
        _LOG.error(
            "eval.gate.config",
            reason="committed baseline is for a different backend; the local fake run "
            "cannot be gated against it. Pass --pipeline-factory with --backend/--corpus/--clock.",
            baseline_backend=baseline.backend,
        )
        return 2

    result = run_variant(
        golden,
        registry,
        DEFAULT_VARIANT,
        top_k=args.top_k,
        backend=args.backend or ("configured" if factory else "fake"),
        corpus=args.corpus,
        clock_label=args.clock,
        retrieval=factory(DEFAULT_VARIANT) if factory else None,
    )
    try:
        report = assert_no_regression(result, baseline)
    except RegressionError as exc:
        _LOG.error("eval.gate.failed", failures=exc.context.get("failures", []))
        return 1
    _LOG.info("eval.gate.passed", baseline_id=baseline.baseline_id, failures=list(report.failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
