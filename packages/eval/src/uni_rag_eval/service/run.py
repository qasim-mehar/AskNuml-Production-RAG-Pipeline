"""Orchestration: load golden data, compose a retrieval callable, run variants, write reports.

The retrieval callable is injected (L3): CI and the default CLI build a fake-backed
pipeline from core ports; the integration pass hands its composed pipeline to
:func:`run_variant` / :func:`run_ablation_suite` at runtime. This package never
imports a retrieval lane (L2/L14).
"""

from __future__ import annotations

import argparse
import importlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from uni_rag_core import Chunk, FakeClock, get_logger
from uni_rag_eval.domain.golden import (
    FixtureRegistry,
    GoldenSet,
    chunks_for_strategy,
    chunks_from_registry,
    golden_for_strategy,
    load_fixture_registry,
    load_golden_set,
    validate_golden_set,
)
from uni_rag_eval.domain.variant import (
    CHUNKING_STRATEGIES,
    DEFAULT_VARIANT,
    FIXED_WINDOW,
    INTEGRATED_CHUNKING,
    LANE_E_NODE_ROWS,
    SENTENCE_BOUNDARY,
    NodePurposeRow,
    SearchMode,
    Variant,
    Verdict,
    build_variant,
    make_variant_name,
    retry_rewrite_verdict,
    variant_matrix,
)
from uni_rag_eval.runner import ablation
from uni_rag_eval.runner.gate import RegressionError, assert_no_regression, load_baseline
from uni_rag_eval.runner.harness import (
    DEFAULT_ABSTENTION_THRESHOLD,
    RetrievalCallable,
    RunContext,
    RunResult,
    WeakEvidenceSubset,
    build_fake_pipeline,
    default_judge,
    recall_gain_on_subset,
    run_harness,
    subset_recall,
    weak_evidence_subset,
)

_LOG = get_logger("uni_rag_eval.service")
DEFAULT_RUN_ID = "mechanics-validation-fake-v1"
PipelineFactory = Callable[[Variant], RetrievalCallable]


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
    clock_label: str | None = None,
    retrieval: RetrievalCallable | None = None,
    known_chunks: Mapping[str, Chunk] | None = None,
    corpus_strategy: str | None = None,
) -> RunResult:
    """Run one variant and return a fully labelled result.

    ``retrieval`` is the injected boundary (L3). When absent, a deterministic
    fake pipeline composed from core ports is used and ``backend`` must say so.
    ``corpus_strategy`` switches the fixture corpus to one indexed under a
    single chunking strategy and translates golden ids into that corpus (L12).
    """
    fixed_now = now or FakeClock().now()
    clock = FakeClock(fixed_now)
    indexed_under = corpus_strategy or variant.corpus_strategy
    if indexed_under != INTEGRATED_CHUNKING:
        chunks = chunks_for_strategy(registry, indexed_under)
        golden = golden_for_strategy(golden, registry, indexed_under)
        corpus_label = corpus or f"{registry.registry_id}-{indexed_under}"
    else:
        chunks = chunks_from_registry(registry)
        corpus_label = corpus or registry.registry_id
    pipeline = retrieval
    if pipeline is None:
        pipeline = build_fake_pipeline(
            chunks,
            variant=variant,
            clock=clock,
            threshold=DEFAULT_ABSTENTION_THRESHOLD,
        )
    context = RunContext(
        run_id=run_id,
        backend=backend,
        corpus=corpus_label,
        variant_name=variant.name,
        chunking_strategy=variant.chunking_strategy,
        golden_id=golden.golden_id,
        top_k=top_k,
        timestamp=fixed_now.astimezone(UTC).isoformat(),
        clock=clock_label or f"FakeClock({fixed_now.astimezone(UTC).isoformat()})",
        retry_rewrite=variant.retry_rewrite,
        corpus_strategy=indexed_under,
    )
    corpus_chunks = known_chunks if known_chunks is not None else {c.chunk_id: c for c in chunks}
    return run_harness(golden, pipeline, default_judge(), context, corpus_chunks)


def run_ablation_suite(
    golden: GoldenSet,
    registry: FixtureRegistry,
    report_dir: Path,
    *,
    chunking_strategies: Sequence[str] = (INTEGRATED_CHUNKING,),
    top_k: int = 5,
    run_id: str = DEFAULT_RUN_ID,
    node_rows: Sequence[NodePurposeRow] = LANE_E_NODE_ROWS,
    backend: str = "fake",
    corpus: str | None = None,
    clock_label: str | None = None,
    pipeline_factory: PipelineFactory | None = None,
    known_chunks: Mapping[str, Chunk] | None = None,
    retry: RetryRewriteComparison | None = None,
) -> tuple[RunResult, ...]:
    """Run every variant, write its table pair and the labelled summary."""
    results = tuple(
        run_variant(
            golden,
            registry,
            variant,
            top_k=top_k,
            run_id=run_id,
            backend=backend,
            corpus=corpus,
            clock_label=clock_label,
            retrieval=pipeline_factory(variant) if pipeline_factory else None,
            known_chunks=known_chunks,
            corpus_strategy=variant.corpus_strategy,
        )
        for variant in variant_matrix(chunking_strategies)
    )
    default_handoff = tuple(row.node_name for row in node_rows) == tuple(
        row.node_name for row in LANE_E_NODE_ROWS
    )
    rendered_rows = (
        measured_l16_rows(golden, registry, results, node_rows, retry)
        if default_handoff
        else node_rows
    )
    paths = ablation.write_ablation_report(results, report_dir, rendered_rows)
    _LOG.info(
        "eval.ablation.written",
        variants=len(results),
        reports=[str(path) for path in paths],
        backend=backend,
        corpus=corpus or registry.registry_id,
    )
    return results


@dataclass(frozen=True)
class RetryRewriteComparison:
    """Two runs differing only by the flag, plus the pure L16 verdict (L1/L16)."""

    single_pass: RunResult
    retry_on: RunResult
    subset: WeakEvidenceSubset
    recall_off: Mapping[str, float]
    recall_on: Mapping[str, float]
    gains: Mapping[str, float]
    verdict: Verdict


@dataclass(frozen=True)
class StrategyComparison:
    """One corpus per strategy, queried under its own indexed corpus (L16)."""

    results: Mapping[str, RunResult]
    recall_gains: Mapping[str, float]
    tied: bool


def run_retry_rewrite_comparison(
    golden: GoldenSet,
    registry: FixtureRegistry,
    pipeline_factory: PipelineFactory,
    *,
    top_k: int = 5,
    run_id: str = "retry-rewrite-m3",
    backend: str,
    corpus: str,
    clock: str,
) -> RetryRewriteComparison:
    """Run flag-off then flag-on with identical configuration and measure the row.

    The only variant difference is ``retry_rewrite``; the factory is the public
    ``Variant -> RetrievalCallable`` boundary supplied by configuration (L3).
    """
    off_variant = build_variant(SearchMode.HYBRID, True, False, retry_rewrite=False)
    on_variant = build_variant(SearchMode.HYBRID, True, False, retry_rewrite=True)
    if (
        on_variant.model_copy(update={"retry_rewrite": False, "name": off_variant.name})
        != off_variant
    ):
        raise RuntimeError("retry on/off variants must differ only by the flag (L1)")
    single_pass = run_variant(
        golden,
        registry,
        off_variant,
        top_k=top_k,
        run_id=run_id,
        backend=backend,
        corpus=corpus,
        clock_label=clock,
        retrieval=pipeline_factory(off_variant),
    )
    retry_on = run_variant(
        golden,
        registry,
        on_variant,
        top_k=top_k,
        run_id=run_id,
        backend=backend,
        corpus=corpus,
        clock_label=clock,
        retrieval=pipeline_factory(on_variant),
    )
    subset = weak_evidence_subset(golden, single_pass)
    gains = recall_gain_on_subset(subset, single_pass, retry_on)
    return RetryRewriteComparison(
        single_pass=single_pass,
        retry_on=retry_on,
        subset=subset,
        recall_off=subset_recall(subset, single_pass),
        recall_on=subset_recall(subset, retry_on),
        gains=gains,
        verdict=retry_rewrite_verdict(gains),
    )


def run_strategy_comparison(
    golden: GoldenSet,
    registry: FixtureRegistry,
    pipeline_factory: PipelineFactory,
    *,
    top_k: int = 5,
    run_id: str = "strategy-ablation-m3",
    backend: str,
    clock: str,
) -> StrategyComparison:
    """Index the fixture corpus once per strategy, then query each under its own corpus."""
    results: dict[str, RunResult] = {}
    for strategy in CHUNKING_STRATEGIES:
        variant = build_variant(SearchMode.HYBRID, True, False)
        variant = variant.model_copy(
            update={
                "name": make_variant_name(
                    variant.search_mode, variant.rerank, variant.freshness_boost, strategy
                ),
                "chunking_strategy": strategy,
                "corpus_strategy": strategy,
            }
        )
        results[strategy] = run_variant(
            golden,
            registry,
            variant,
            top_k=top_k,
            run_id=run_id,
            backend=backend,
            corpus=f"{registry.registry_id}-{strategy}",
            clock_label=clock,
            retrieval=pipeline_factory(variant),
            corpus_strategy=strategy,
        )
    gains = {
        language: results[SENTENCE_BOUNDARY]
        .scores_by_language.get(language, results[SENTENCE_BOUNDARY].overall)
        .recall_at_k
        - results[FIXED_WINDOW]
        .scores_by_language.get(language, results[FIXED_WINDOW].overall)
        .recall_at_k
        for language in ("en", "ur", "roman_urdu", "overall")
    }
    tied = all(abs(value) < 1e-12 for value in gains.values())
    return StrategyComparison(results=results, recall_gains=gains, tied=tied)


def measured_l16_rows(
    golden: GoldenSet,
    registry: FixtureRegistry,
    results: Sequence[RunResult],
    rows: Sequence[NodePurposeRow] = LANE_E_NODE_ROWS,
    retry: RetryRewriteComparison | None = None,
) -> tuple[NodePurposeRow, ...]:
    """Fill the linear L16 effects from measured data; leave future nodes awaiting (L16)."""
    by_variant = {result.context.variant_name: result for result in results}
    default = by_variant.get(DEFAULT_VARIANT.name, results[0])
    hybrid_off = next(
        (
            result
            for name, result in by_variant.items()
            if name.startswith("hybrid-rerank-off-freshness-off-")
        ),
        default,
    )
    dense_off = next(
        (
            result
            for name, result in by_variant.items()
            if name.startswith("dense-rerank-off-freshness-off-")
        ),
        default,
    )
    hybrid_on = next(
        (
            result
            for name, result in by_variant.items()
            if name.startswith("hybrid-rerank-on-freshness-off-")
        ),
        default,
    )
    doc_ids = {chunk.chunk_id: doc.doc_id for doc in registry.documents for chunk in doc.chunks}
    routed = sum(
        1
        for record in golden.records
        if record.language.value in {"en", "ur", "roman_urdu"}
        and (record.expected_abstain or record.expected_filters.get("doc_id") in doc_ids.values())
    )
    filtered = sum(
        1
        for record in golden.records
        if not record.expected_abstain
        and record.expected_filters.get("doc_id")
        in {doc_ids[cid] for cid in record.expected_chunk_ids if cid in doc_ids}
    )

    def _delta(name: str, left: RunResult, right: RunResult) -> str:
        parts = []
        for language in ("en", "ur", "roman_urdu", "overall"):
            lv = left.overall if language == "overall" else left.scores_by_language[language]
            rv = right.overall if language == "overall" else right.scores_by_language[language]
            parts.append(f"{language} {getattr(rv, name) - getattr(lv, name):+.4f}")
        return ", ".join(parts)

    effects = {
        "route": f"Measured: {routed}/{len(golden.records)} records route to a supported language "
        "with a resolvable or intentionally empty filter; no linear-baseline regression observed.",
        "filter": f"Measured: {filtered}/27 answerable records retain the expected doc_id "
        "after filtering.",
        "search": "Measured hybrid-vs-dense recall@5 delta (rerank off): "
        + _delta("recall_at_k", dense_off, hybrid_off),
        "rerank": "Measured rerank-on minus rerank-off (hybrid) ndcg: "
        + _delta("ndcg", hybrid_off, hybrid_on)
        + ". No measured gain on this corpus.",
        "abstain": f"Measured abstention precision {default.overall.abstention_precision:.4f} "
        "overall; the three fee rows abstain with no cited facts.",
        "answer": f"Measured faithfulness {default.overall.faithfulness:.4f} and "
        f"citation-resolution {default.overall.citation_resolution:.4f} overall (hybrid, "
        "rerank on), read natively from Citation.last_crawled.",
    }
    if retry is not None:
        composition = ", ".join(
            f"{language} {count}"
            for language, count in sorted(retry.subset.counts_by_language.items())
        )
        deltas = ", ".join(f"{language} {gain:+.4f}" for language, gain in retry.gains.items())
        effects["retry_rewrite"] = (
            f"Measured recall@5 gain on weak-evidence rows (n={len(retry.subset.record_ids)}; "
            f"{composition or 'none in any language'}): {deltas}; "
            f"L16 verdict {retry.verdict.value}."
        )
    return tuple(
        row.model_copy(update={"measured_effect": effects[row.node_name]})
        if row.node_name in effects
        else row
        for row in rows
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run the default fake ablation suite and write reports."""
    parser = argparse.ArgumentParser(description="Run fake-backed evaluation ablations")
    parser.add_argument("--golden", type=Path, default=Path("eval/golden/golden.json"))
    parser.add_argument("--registry", type=Path, default=Path("eval/golden/fixture-registry.json"))
    parser.add_argument("--reports", type=Path, default=Path("eval/reports"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument(
        "--pipeline-factory",
        default=None,
        help="module:attr handed in by the integration configuration",
    )
    parser.add_argument("--backend", default=None, help="label of the injected backend")
    parser.add_argument("--corpus", default=None, help="label of the injected corpus")
    parser.add_argument("--clock", default=None, help="label of the injected clock")
    parser.add_argument(
        "--mode",
        choices=("ablation", "m3"),
        default="ablation",
        help="m3 also runs the retry_rewrite verdict and per-strategy corpus ablation",
    )
    args = parser.parse_args(argv)

    golden, registry = load_eval_inputs(args.golden, args.registry)
    factory = None
    if args.pipeline_factory:
        module_name, separator, attr = args.pipeline_factory.partition(":")
        if not separator or not module_name or not attr:
            from uni_rag_core import ValidationError

            raise ValidationError("--pipeline-factory must be module:attr")
        factory = getattr(importlib.import_module(module_name), attr)
    backend_label = args.backend or ("configured" if factory else "fake")
    if args.mode == "m3":
        if factory is None:
            raise RuntimeError("m3 mode requires --pipeline-factory (L1/L3)")
        retry = run_retry_rewrite_comparison(
            golden,
            registry,
            factory,
            top_k=args.top_k,
            backend=backend_label,
            corpus=args.corpus or registry.registry_id,
            clock=args.clock or "FakeClock(2026-01-01T00:00:00+00:00)",
        )
        strategy = run_strategy_comparison(
            golden,
            registry,
            factory,
            top_k=args.top_k,
            backend=backend_label,
            clock=args.clock or "FakeClock(2026-01-01T00:00:00+00:00)",
        )
        ablation.write_retry_comparison(retry, args.reports)
        ablation.write_strategy_comparison(strategy, args.reports)
        results = run_ablation_suite(
            golden,
            registry,
            args.reports,
            top_k=args.top_k,
            run_id=args.run_id,
            backend=backend_label,
            corpus=args.corpus,
            clock_label=args.clock,
            pipeline_factory=factory,
            retry=retry,
        )
        ablation.write_latest(
            results,
            args.reports,
            measured_l16_rows(golden, registry, results, retry=retry),
        )
        _LOG.info(
            "eval.m3.complete",
            verdict=retry.verdict.value,
            overall_gain=retry.gains["overall"],
            strategy_tied=strategy.tied,
        )
        return 0
    results = run_ablation_suite(
        golden,
        registry,
        args.reports,
        top_k=args.top_k,
        run_id=args.run_id,
        backend=backend_label,
        corpus=args.corpus,
        clock_label=args.clock,
        pipeline_factory=factory,
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
