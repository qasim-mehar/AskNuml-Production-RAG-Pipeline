"""Markdown/CSV ablation tables: one per variant plus a summary (L1/L7/L16)."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Sequence
from pathlib import Path

from uni_rag_core import ValidationError
from uni_rag_eval.domain.golden import REQUIRED_LANGUAGES
from uni_rag_eval.domain.variant import NodePurposeRow
from uni_rag_eval.runner.harness import MetricScores, RunResult

_METRIC_COLUMNS: tuple[tuple[str, str], ...] = (
    ("recall_at_k", "recall@{k}"),
    ("mrr", "mrr"),
    ("ndcg", "ndcg"),
    ("faithfulness", "faithfulness"),
    ("abstention_precision", "abstention_precision"),
)
_LANGUAGE_ORDER: tuple[str, ...] = (
    *(language.value for language in REQUIRED_LANGUAGES),
    "overall",
)


def _scores_for(result: RunResult, language: str) -> MetricScores:
    scores = result.overall if language == "overall" else result.scores_by_language.get(language)
    if scores is None:
        raise ValidationError(
            "Run result lacks a required language row", context={"language": language}
        )
    return scores


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _metadata_lines(result: RunResult) -> list[str]:
    context = result.context
    return [
        f"- backend: `{context.backend}`",
        f"- corpus: `{context.corpus}`",
        f"- golden set: `{context.golden_id}`",
        f"- variant: `{context.variant_name}` (chunking: `{context.chunking_strategy}`)",
        f"- top_k: `{context.top_k}`",
        f"- timestamp: `{context.timestamp}`",
        f"- config fingerprint: `{context.fingerprint()}`",
        "- scoring: retrieval metrics pool answerable ground truth; faithfulness pools "
        "answered records; abstention precision pools all records.",
        "- mechanics validation on a fake backend only; a zero row is a measured fake "
        "result, not a quality verdict.",
    ]


def _rows(result: RunResult) -> list[tuple[str, ...]]:
    header = (
        "language",
        "n_questions",
        "n_answerable",
        "n_answered",
        f"recall@{result.context.top_k}",
        *[label for field, label in _METRIC_COLUMNS if field != "recall_at_k"],
    )
    body: list[tuple[str, ...]] = []
    for language in _LANGUAGE_ORDER:
        scores = _scores_for(result, language)
        body.append(
            (
                language,
                str(scores.n_records),
                str(scores.n_answerable),
                str(scores.n_answered),
                *[_fmt(getattr(scores, field)) for field, _ in _METRIC_COLUMNS],
            )
        )
    return [header, *body]


def _markdown_table(rows: Sequence[tuple[str, ...]]) -> str:
    header, *body = rows
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def _csv_table(rows: Sequence[tuple[str, ...]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return buffer.getvalue()


def _write_text(path: Path, text: str) -> Path:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


def variant_table_markdown(result: RunResult) -> str:
    """Render the full labelled table for one variant."""
    title = f"# Ablation: {result.context.variant_name}"
    return "\n".join([title, "", *_metadata_lines(result), "", _markdown_table(_rows(result)), ""])


def variant_table_csv(result: RunResult) -> str:
    """Render the CSV equivalent of :func:`variant_table_markdown`."""
    return _csv_table(_rows(result))


def write_variant_tables(result: RunResult, report_dir: Path) -> tuple[Path, Path]:
    """Write ``<variant>.md`` and ``<variant>.csv`` into ``report_dir``."""
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = f"variant-{_slug(result.context.variant_name)}"
    markdown = _write_text(report_dir / f"{stem}.md", variant_table_markdown(result))
    csv_path = _write_text(report_dir / f"{stem}.csv", variant_table_csv(result))
    return markdown, csv_path


def l16_section(node_rows: Sequence[NodePurposeRow]) -> str:
    """Render the L16 node-purpose table, empty-and-waiting when Lane E has not handed off."""
    header = ("node", "purpose", "required_eval_row", "measured_effect")
    rows = (
        [
            header,
            *[
                (row.node_name, row.purpose, row.required_eval_row, row.measured_effect)
                for row in node_rows
            ],
        ]
        if node_rows
        else [
            header,
            (
                "_awaiting Lane E handoff_",
                "node purposes pending",
                "eval rows pending",
                "not measured",
            ),
        ]
    )
    return "\n".join(
        [
            "## L16 graph-node eval rows",
            "",
            "One row per graph node purpose. Populate from Lane E's handoff; do not invent effects.",
            "",
            _markdown_table(rows),
            "",
        ]
    )


def summary_rows(results: Sequence[RunResult]) -> list[tuple[str, ...]]:
    """Rows keyed by variant and language, so every table keeps the L7 split visible."""
    header = (
        "variant",
        "language",
        f"recall@{results[0].context.top_k}" if results else "recall@k",
        *[label for field, label in _METRIC_COLUMNS if field != "recall_at_k"],
    )
    rows: list[tuple[str, ...]] = [header]
    for result in sorted(results, key=lambda item: item.context.variant_name):
        for language in _LANGUAGE_ORDER:
            scores = _scores_for(result, language)
            rows.append(
                (
                    result.context.variant_name,
                    language,
                    *[_fmt(getattr(scores, field)) for field, _ in _METRIC_COLUMNS],
                )
            )
    return rows


def summary_markdown(results: Sequence[RunResult], node_rows: Sequence[NodePurposeRow]) -> str:
    """Render the comparison table and the L16 table (L7/L16)."""
    first = results[0].context if results else None
    header = [
        "# Ablation summary",
        "",
        f"- variants: `{len(results)}`",
        f"- backend: `{first.backend if first else 'unknown'}`",
        f"- corpus: `{first.corpus if first else 'unknown'}`",
        f"- golden set: `{first.golden_id if first else 'unknown'}`",
        f"- top_k: `{first.top_k if first else 'unknown'}`",
        "- all numbers are mechanics validation on the fake backend, not a quality claim.",
        "",
        _markdown_table(summary_rows(results)),
        "",
    ]
    return "\n".join([*header, l16_section(node_rows)])


def write_summary(
    results: Sequence[RunResult], report_dir: Path, node_rows: Sequence[NodePurposeRow] = ()
) -> tuple[Path, Path]:
    """Write ``summary.md`` and ``summary.csv``."""
    report_dir.mkdir(parents=True, exist_ok=True)
    markdown = _write_text(report_dir / "summary.md", summary_markdown(results, node_rows))
    csv_path = _write_text(report_dir / "summary.csv", _csv_table(summary_rows(results)))
    return markdown, csv_path


def write_ablation_report(
    results: Sequence[RunResult], report_dir: Path, node_rows: Sequence[NodePurposeRow] = ()
) -> list[Path]:
    """Write one table pair per variant plus the summary pair."""
    paths: list[Path] = []
    for result in results:
        paths.extend(write_variant_tables(result, report_dir))
    paths.extend(write_summary(results, report_dir, node_rows))
    return paths
