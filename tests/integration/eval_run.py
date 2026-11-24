"""Run Lane F's harness against the integrated pipeline and record labelled reports.

This module only *calls* Lane F's harness and gate. It never edits the golden
set, the baseline or any threshold (L1, L14). Reports are written under
``eval/reports/`` with an explicit backend label on every table.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC
from pathlib import Path

from tests.factories import FIXED_TIME
from tests.integration.composition import build_context, parser_backend
from tests.integration.selection import AdapterSelection
from uni_rag_core import FakeClock, Settings
from uni_rag_core.schemas import Chunk
from uni_rag_eval.domain.golden import chunks_from_registry
from uni_rag_eval.domain.variant import DEFAULT_VARIANT
from uni_rag_eval.runner.gate import Baseline, compare_to_baseline, load_baseline
from uni_rag_eval.runner.harness import RunContext, RunResult, default_judge, run_harness
from uni_rag_eval.service.run import load_eval_inputs, run_variant

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GOLDEN = _REPO_ROOT / "eval" / "golden" / "golden.json"
_REGISTRY = _REPO_ROOT / "eval" / "golden" / "fixture-registry.json"
_BASELINE = _REPO_ROOT / "eval" / "golden" / "baseline.json"
_REPORTS = _REPO_ROOT / "eval" / "reports"
_RUN_ID = "integrated-offline-v1"
_TOP_K = 5


def integration_settings() -> Settings:
    """Typed settings for the local fixture/registry corpus (L8)."""
    return Settings(
        environment="local",
        qdrant_url="http://127.0.0.1:6333",
        postgres_dsn="postgresql://uni_rag:uni_rag@127.0.0.1:5432/uni_rag",
        minio_endpoint="http://127.0.0.1:9000",
        embedding_dimension=16,
        default_top_k=_TOP_K,
        abstention_threshold=0.35,
    )


def offline_selection() -> AdapterSelection:
    """Real adapters that run without Docker or keys; every fake stays CI-default."""
    return replace(
        AdapterSelection.ci_default(),
        parser="docling",
        chunking="strategies",
        vector_store="qdrant_local",
        embedder="google_genai",
        llm="google_genai",
    )


def run_integrated(chunks: Sequence[Chunk], settings: Settings) -> RunResult:
    """Score the golden set through Lane E's pipeline with real adapters behind ports."""
    golden, _ = load_eval_inputs(_GOLDEN, _REGISTRY)
    selection = offline_selection()
    context = build_context(selection, settings, chunks=chunks, clock=FakeClock(FIXED_TIME))
    # Populate the store: without this, dense search returns nothing and "hybrid"
    # numbers silently degrade to lexical-only (L1).
    context.vector_store.upsert(
        [(chunk, context.embedder.embed([chunk.text])[0]) for chunk in chunks]
    )
    run_context = RunContext(
        run_id=_RUN_ID,
        backend=f"{selection.backend_label()}|parser_engine={parser_backend()}",
        corpus="fixture-corpus-v1",
        variant_name=DEFAULT_VARIANT.name,
        chunking_strategy="fixed_window+sentence_boundary",
        golden_id=golden.golden_id,
        top_k=_TOP_K,
        timestamp=FIXED_TIME.astimezone(UTC).isoformat(),
    )
    return run_harness(golden, context.ask, default_judge(), run_context)


def _metric_row(language: str, scores: object) -> str:
    fields = ("recall_at_k", "mrr", "ndcg", "faithfulness", "abstention_precision")
    cells = " | ".join(f"{getattr(scores, field):.4f}" for field in fields)
    return f"| {language} | {cells} |"


def write_report(result: RunResult, baseline: Baseline, path: Path) -> None:
    """Write a labelled table plus a baseline metric comparison; no threshold changes."""
    lines = [
        "# First integrated-pipeline numbers",
        "",
        f"- run_id: `{result.context.run_id}`",
        f"- backend: `{result.context.backend}`",
        f"- corpus: `{result.context.corpus}`",
        f"- clock: `FakeClock({FIXED_TIME.isoformat()})` (pinned for determinism)",
        f"- golden set: `{result.context.golden_id}`",
        f"- top_k: `{result.context.top_k}`",
        "- no live calls: providers' live flag is off and no key is supplied through typed settings; offline transports only.",
        "- answers are Lane E's raw pipeline outputs; no integration-side provenance patching.",
        "",
        f"| language | recall@{_TOP_K} | mrr | ndcg | faithfulness | abstention_precision |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for language, scores in {**result.scores_by_language, "overall": result.overall}.items():
        lines.append(_metric_row(language, scores))
    lines.extend(
        [
            "",
            "## Baseline metric comparison",
            "",
            "| language.metric | integrated | baseline threshold | delta |",
            "| --- | --- | --- | --- |",
        ]
    )
    comparison = compare_to_baseline(result, baseline)
    for language, thresholds in sorted(baseline.thresholds.items()):
        language_scores = {**result.scores_by_language, "overall": result.overall}.get(language)
        if language_scores is None:
            lines.append(f"| {language} | missing | - | - |")
            continue
        for metric, threshold in sorted(thresholds.items()):
            actual = float(getattr(language_scores, metric))
            lines.append(
                f"| {language}.{metric} | {actual:.6f} | {threshold:.6f} | {actual - threshold:+.6f} |"
            )
    metric_failures = [item for item in comparison.failures if not item.startswith("label ")]
    lines.extend(
        [
            "",
            "Baseline labels differ (fake backend); label mismatches are not metric "
            "regressions. No threshold was loosened.",
            f"Gate failures recorded by Lane F's comparator: {list(comparison.failures)}",
        ]
    )
    if metric_failures:
        lines.extend(
            [
                "",
                "Filed for Lane E (ranking/scoring), not fixed here: "
                + "; ".join(metric_failures)
                + ". Thresholds stay at their committed values.",
            ]
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the fake-baseline check and the integrated run; write both reports."""
    parser = argparse.ArgumentParser(description="Run the integrated evaluation harness")
    parser.add_argument("--reports", type=Path, default=_REPORTS)
    args = parser.parse_args(argv)

    golden, registry = load_eval_inputs(_GOLDEN, _REGISTRY)
    settings = integration_settings()
    baseline = load_baseline(_BASELINE)

    fake_result = run_variant(golden, registry, DEFAULT_VARIANT, top_k=_TOP_K)
    fake_comparison = compare_to_baseline(fake_result, baseline)
    if [item for item in fake_comparison.failures if "label" not in item]:
        return 1

    chunks = chunks_from_registry(registry)
    integrated = run_integrated(chunks, settings)
    write_report(integrated, baseline, args.reports / "integrated-offline.md")
    integrated_comparison = compare_to_baseline(integrated, baseline)
    metric_failures = [
        item for item in integrated_comparison.failures if not item.startswith("label ")
    ]
    if metric_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
