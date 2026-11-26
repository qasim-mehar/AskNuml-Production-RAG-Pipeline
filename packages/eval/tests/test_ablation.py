"""Ablation table emission: one table per variant, summary, L16 rows, determinism."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from uni_rag_core import ValidationError
from uni_rag_eval.domain.golden import load_fixture_registry, load_golden_set
from uni_rag_eval.domain.variant import (
    DEFAULT_VARIANT,
    FIXED_WINDOW,
    INTEGRATED_CHUNKING,
    LANE_E_NODE_ROWS,
    SENTENCE_BOUNDARY,
    NodePurposeRow,
    variant_matrix,
)
from uni_rag_eval.runner.ablation import _slug, variant_table_markdown
from uni_rag_eval.service.run import measured_l16_rows, run_ablation_suite, run_variant

ROOT = Path(__file__).resolve().parents[3]


def _inputs() -> Any:
    golden = load_golden_set(
        json.loads((ROOT / "eval/golden/golden.json").read_text(encoding="utf-8"))
    )
    registry = load_fixture_registry(
        json.loads((ROOT / "eval/golden/fixture-registry.json").read_text(encoding="utf-8"))
    )
    return golden, registry


def test_one_table_pair_per_variant_plus_summary(tmp_path: Path) -> None:
    golden, registry = _inputs()
    results = run_ablation_suite(golden, registry, tmp_path)
    assert len(results) == len(variant_matrix()) == 12

    files = sorted(path.name for path in tmp_path.iterdir())
    assert len(files) == 26
    assert "summary.md" in files and "summary.csv" in files
    for result in results:
        stem = f"variant-{_slug(result.context.variant_name)}"
        assert f"{stem}.md" in files
        assert f"{stem}.csv" in files

    for result in results:
        table = (tmp_path / f"variant-{_slug(result.context.variant_name)}.md").read_text(
            encoding="utf-8"
        )
        assert "`fake`" in table
        assert "`fixture-corpus-v1`" in table
        assert "`2026-01-01T00:00:00+00:00`" in table
        assert "- clock: `" in table
        assert "- top_k (k): `5`" in table
        assert "citation_resolution" in table
        for language in ("| en |", "| ur |", "| roman_urdu |", "| overall |"):
            assert language in table

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "- clock: `" in summary and "- top_k (k): `5`" in summary
    assert "not a quality claim" in summary
    for name in ("route", "filter", "search", "rerank", "abstain", "answer"):
        assert f"| {name} |" in summary
    assert summary.count("| awaiting measurement |") == 3
    assert "Removed after E3" in summary


def test_variant_matrix_uses_published_strategies_and_has_twelve_variants() -> None:
    matrix = variant_matrix()
    assert len(matrix) == 12
    assert all(FIXED_WINDOW in v.chunking_strategy for v in matrix)
    assert all(SENTENCE_BOUNDARY in v.chunking_strategy for v in matrix)
    assert all("awaiting" not in v.name for v in matrix)
    assert {v.name for v in matrix} == {v.name for v in variant_matrix((INTEGRATED_CHUNKING,))}


def test_l16_rows_carry_lane_e_purposes_and_only_measured_linear_effects() -> None:
    names = [row.node_name for row in LANE_E_NODE_ROWS]
    assert names == [
        "route",
        "filter",
        "search",
        "rerank",
        "abstain",
        "answer",
        "retry_rewrite",
        "clarify",
        "multihop",
        "checkpoint_followup",
    ]
    linear_names = {"route", "filter", "search", "rerank", "abstain", "answer"}
    measured = [
        row
        for row in LANE_E_NODE_ROWS
        if row.node_name in linear_names and row.measured_effect != "awaiting measurement"
    ]
    awaiting = [row for row in LANE_E_NODE_ROWS if row.measured_effect == "awaiting measurement"]
    assert [row.node_name for row in measured] == [
        "route",
        "filter",
        "search",
        "rerank",
        "abstain",
        "answer",
    ]
    assert [row.node_name for row in awaiting] == [
        "clarify",
        "multihop",
        "checkpoint_followup",
    ]
    retry_row = next(row for row in LANE_E_NODE_ROWS if row.node_name == "retry_rewrite")
    assert retry_row.measured_effect.startswith("Removed after E3")
    assert "dormant flags" in retry_row.measured_effect
    assert "live-transport re-run" in retry_row.measured_effect
    assert all(row.required_eval_row for row in LANE_E_NODE_ROWS)


def test_l16_linear_effects_are_computed_from_the_measurements(tmp_path: Path) -> None:
    golden, registry = _inputs()
    results = run_ablation_suite(golden, registry, tmp_path)
    effects = {
        row.node_name: row.measured_effect for row in measured_l16_rows(golden, registry, results)
    }
    by_name = {result.context.variant_name: result for result in results}
    dense = next(r for n, r in by_name.items() if n.startswith("dense-rerank-off-freshness-off-"))
    hybrid_off = next(
        r for n, r in by_name.items() if n.startswith("hybrid-rerank-off-freshness-off-")
    )
    hybrid_on = next(
        r for n, r in by_name.items() if n.startswith("hybrid-rerank-on-freshness-off-")
    )
    default = by_name[DEFAULT_VARIANT.name]
    assert "30/30" in effects["route"]
    assert "27/27" in effects["filter"]
    search_delta = hybrid_off.overall.recall_at_k - dense.overall.recall_at_k
    assert "recall@5" in effects["search"] and f"{search_delta:+.4f}" in effects["search"]
    rerank_delta = hybrid_on.overall.ndcg - hybrid_off.overall.ndcg
    assert "ndcg" in effects["rerank"] and f"{rerank_delta:+.4f}" in effects["rerank"]
    assert f"{default.overall.abstention_precision:.4f}" in effects["abstain"]
    assert f"{default.overall.faithfulness:.4f}" in effects["answer"]
    assert f"{default.overall.citation_resolution:.4f}" in effects["answer"]
    assert "Removed after E3" in effects["retry_rewrite"]
    assert all(
        effects[name] == "awaiting measurement"
        for name in ("clarify", "multihop", "checkpoint_followup")
    )


def test_ablation_reports_are_byte_identical_for_identical_inputs(tmp_path: Path) -> None:
    golden, registry = _inputs()
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    run_ablation_suite(golden, registry, first_dir)
    run_ablation_suite(golden, registry, second_dir)
    first_files = sorted(first_dir.iterdir())
    second_files = sorted(second_dir.iterdir())
    assert [path.name for path in first_files] == [path.name for path in second_files]
    for first, second in zip(first_files, second_files, strict=True):
        assert first.read_bytes() == second.read_bytes()


def test_a_missing_language_row_is_an_error_not_a_silent_blank() -> None:
    golden, registry = _inputs()
    result = run_variant(golden, registry, DEFAULT_VARIANT, top_k=5)
    without_urdu = replace(
        result,
        scores_by_language={
            key: value for key, value in result.scores_by_language.items() if key != "ur"
        },
    )
    with pytest.raises(ValidationError, match="lacks a required language"):
        variant_table_markdown(without_urdu)


def test_l16_node_rows_are_rendered_from_handoff_data(tmp_path: Path) -> None:
    golden, registry = _inputs()
    row = NodePurposeRow(
        node_name="retry_on_weak_retrieval",
        purpose="Rewrite the query when top evidence is below threshold",
        required_eval_row="recall@5 delta vs no-retry",
        measured_effect="pending Lane E handoff",
    )
    run_ablation_suite(golden, registry, tmp_path, node_rows=[row])
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "retry_on_weak_retrieval" in summary
    assert "recall@5 delta vs no-retry" in summary
