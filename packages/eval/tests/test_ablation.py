"""Ablation table emission: one table per variant, summary, L16 rows, determinism."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from uni_rag_core import ValidationError
from uni_rag_eval.domain.golden import load_fixture_registry, load_golden_set
from uni_rag_eval.domain.variant import DEFAULT_VARIANT, NodePurposeRow, variant_matrix
from uni_rag_eval.runner.ablation import variant_table_markdown
from uni_rag_eval.service.run import run_ablation_suite, run_variant

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
        stem = f"variant-{result.context.variant_name}"
        assert f"{stem}.md" in files
        assert f"{stem}.csv" in files

    for result in results:
        table = (tmp_path / f"variant-{result.context.variant_name}.md").read_text(encoding="utf-8")
        assert "`fake`" in table
        assert "`fixture-corpus-v1`" in table
        assert "`2026-01-01T00:00:00+00:00`" in table
        for language in ("| en |", "| ur |", "| roman_urdu |", "| overall |"):
            assert language in table

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "awaiting Lane E handoff" in summary
    assert "not a quality claim" in summary


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
