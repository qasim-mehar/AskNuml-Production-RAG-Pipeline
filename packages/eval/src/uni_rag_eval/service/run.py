"""Orchestration: load golden data, compose fakes, run variants, write reports."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from uni_rag_core import FakeClock, get_logger
from uni_rag_eval.domain.golden import (
    FixtureRegistry,
    GoldenSet,
    chunks_from_registry,
    load_fixture_registry,
    load_golden_set,
    validate_golden_set,
)
from uni_rag_eval.domain.variant import (
    AWAITING_LANE_C,
    DEFAULT_VARIANT,
    NodePurposeRow,
    Variant,
    variant_matrix,
)
from uni_rag_eval.runner import ablation
from uni_rag_eval.runner.gate import RegressionError, assert_no_regression, load_baseline
from uni_rag_eval.runner.harness import (
    DEFAULT_ABSTENTION_THRESHOLD,
    RunContext,
    RunResult,
    build_fake_pipeline,
    default_judge,
    run_harness,
)

_LOG = get_logger("uni_rag_eval.service")
DEFAULT_RUN_ID = "mechanics-validation-fake-v1"


def _read_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        from uni_rag_core import ValidationError

        raise ValidationError("Cannot read evaluation JSON", context={"path": str(path)}) from exc
    if not isinstance(payload, dict):
        from uni_rag_core import ValidationError

        raise ValidationError("Evaluation JSON must be an object", context={"path": str(path)})
    return payload


def load_eval_inputs(golden_path: Path, registry_path: Path) -> tuple[GoldenSet, FixtureRegistry]:
    """Load and validate the golden set against the fixture corpus registry."""
    golden = load_golden_set(_read_payload(golden_path))
    registry = load_fixture_registry(_read_payload(registry_path))
    root = golden_path.resolve().parents[2]
    verified = {doc.source_path for doc in registry.documents if (root / doc.source_path).is_file()}
    validate_golden_set(golden, registry, verified)
    _LOG.info(
        "eval.inputs.loaded",
        golden_id=golden.golden_id,
        registry_id=registry.registry_id,
        questions=len(golden.records),
    )
    return golden, registry


def run_variant(
    golden: GoldenSet,
    registry: FixtureRegistry,
    variant: Variant,
    *,
    top_k: int = 5,
    run_id: str = DEFAULT_RUN_ID,
    backend: str = "fake",
    corpus: str | None = None,
    now: datetime | None = None,
) -> RunResult:
    """Run one variant on the fake-backed pipeline composed from core ports."""
    fixed_now = now or FakeClock().now()
    clock = FakeClock(fixed_now)
    pipeline = build_fake_pipeline(
        chunks_from_registry(registry),
        variant=variant,
        clock=clock,
        threshold=DEFAULT_ABSTENTION_THRESHOLD,
    )
    context = RunContext(
        run_id=run_id,
        backend=backend,
        corpus=corpus or registry.registry_id,
        variant_name=variant.name,
        chunking_strategy=variant.chunking_strategy,
        golden_id=golden.golden_id,
        top_k=top_k,
        timestamp=fixed_now.astimezone(UTC).isoformat(),
    )
    return run_harness(golden, pipeline, default_judge(), context)


def run_ablation_suite(
    golden: GoldenSet,
    registry: FixtureRegistry,
    report_dir: Path,
    *,
    chunking_strategies: Sequence[str] = (AWAITING_LANE_C,),
    top_k: int = 5,
    run_id: str = DEFAULT_RUN_ID,
    node_rows: Sequence[NodePurposeRow] = (),
) -> tuple[RunResult, ...]:
    """Run every variant, write its table pair and the labelled summary."""
    results = tuple(
        run_variant(golden, registry, variant, top_k=top_k, run_id=run_id)
        for variant in variant_matrix(chunking_strategies)
    )
    paths = ablation.write_ablation_report(results, report_dir, node_rows)
    _LOG.info(
        "eval.ablation.written",
        variants=len(results),
        reports=[str(path) for path in paths],
        backend="fake",
        corpus=registry.registry_id,
    )
    return results


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run the fake ablation suite and write reports."""
    parser = argparse.ArgumentParser(description="Run fake-backed evaluation ablations")
    parser.add_argument("--golden", type=Path, default=Path("eval/golden/golden.json"))
    parser.add_argument("--registry", type=Path, default=Path("eval/golden/fixture-registry.json"))
    parser.add_argument("--reports", type=Path, default=Path("eval/reports"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--baseline", type=Path, default=None)
    args = parser.parse_args(argv)

    golden, registry = load_eval_inputs(args.golden, args.registry)
    results = run_ablation_suite(
        golden, registry, args.reports, top_k=args.top_k, run_id=args.run_id
    )
    if args.baseline is not None:
        baseline = load_baseline(args.baseline)
        gate_result = next(
            (item for item in results if item.context.variant_name == DEFAULT_VARIANT.name), None
        )
        if gate_result is None:
            _LOG.error("eval.gate.failed", reason="default variant not in matrix")
            return 1
        try:
            report = assert_no_regression(gate_result, baseline)
        except RegressionError as exc:
            _LOG.error("eval.gate.failed", failures=exc.context.get("failures", []))
            return 1
        _LOG.info(
            "eval.gate.passed", baseline_id=baseline.baseline_id, failures=list(report.failures)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
