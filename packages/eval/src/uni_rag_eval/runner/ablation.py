"""Markdown/CSV ablation tables: one per variant plus a summary (L1/L7/L16)."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from uni_rag_core import ValidationError
from uni_rag_eval.domain.feedback import FEEDBACK_BACKEND_MARKER
from uni_rag_eval.domain.golden import REQUIRED_LANGUAGES
from uni_rag_eval.domain.variant import CHUNKING_STRATEGIES, NodePurposeRow
from uni_rag_eval.runner.harness import MetricScores, RunResult

if TYPE_CHECKING:
    from uni_rag_eval.service.run import RetryRewriteComparison, StrategyComparison

_METRIC_COLUMNS: tuple[tuple[str, str], ...] = (
    ("recall_at_k", "recall@{k}"),
    ("mrr", "mrr"),
    ("ndcg", "ndcg"),
    ("faithfulness", "faithfulness"),
    ("citation_resolution", "citation_resolution"),
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


def adr0010_strip_label(backend: str) -> str:
    """State which ADR-0010 payload strip produced the numbers (L1)."""
    if "strip_source=real-adapter" in backend:
        return "real D2 adapter boundary strip"
    if "strip_source=in-memory" in backend:
        return "labelled in-memory boundary strip (D2 not merged)"
    return "unlabelled strip — backend must name one (L1)"


def _feedback_label_line(backend: str) -> list[str]:
    """State the feedback input honestly when the backend label declares it (L1/L5)."""
    if FEEDBACK_BACKEND_MARKER in backend:
        return [
            "- feedback input: labelled offline fixture transcript, NOT live user feedback "
            "(ADR 0009)."
        ]
    return []


def _metadata_lines(result: RunResult) -> list[str]:
    context = result.context
    return [
        f"- backend: `{context.backend}`",
        f"- ADR-0010 strip: `{adr0010_strip_label(context.backend)}`",
        f"- corpus: `{context.corpus}`",
        f"- golden set: `{context.golden_id}`",
        f"- variant: `{context.variant_name}` (chunking: `{context.chunking_strategy}`)",
        f"- clock: `{context.clock}`",
        f"- top_k (k): `{context.top_k}`",
        *_feedback_label_line(context.backend),
        f"- timestamp: `{context.timestamp}`",
        f"- config fingerprint: `{context.fingerprint()}`",
        "- scoring: retrieval metrics pool answerable ground truth; faithfulness and "
        "citation-resolution pool answered records; abstention precision pools all records.",
        (
            "- mechanics validation on a fake backend only; a zero row is a measured fake "
            "result, not a quality verdict."
            if context.backend == "fake"
            else "- first integrated-pipeline run; adapters are real but offline, no live "
            "provider or network call; a zero row is a measured result (L1)."
        ),
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
        f"- ADR-0010 strip: `{adr0010_strip_label(first.backend if first else '')}`",
        f"- corpus: `{first.corpus if first else 'unknown'}`",
        f"- golden set: `{first.golden_id if first else 'unknown'}`",
        f"- clock: `{first.clock if first else 'unknown'}`",
        f"- top_k (k): `{first.top_k if first else 'unknown'}`",
        *_feedback_label_line(first.backend if first else ""),
        (
            "- all numbers are mechanics validation on the fake backend, not a quality claim."
            if first and first.backend == "fake"
            else "- all numbers are from the labelled integrated backend; offline adapters, "
            "no live provider. Earlier fake-backend mechanics numbers stay separate."
        ),
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


def _comparison_labels(results: Sequence[RunResult]) -> list[str]:
    first = results[0].context if results else None
    return [
        f"- backend: `{first.backend if first else 'unknown'}`",
        f"- ADR-0010 strip: `{adr0010_strip_label(first.backend if first else '')}`",
        f"- clock: `{first.clock if first else 'unknown'}`",
        f"- golden set: `{first.golden_id if first else 'unknown'}`",
        f"- top_k (k): `{first.top_k if first else 'unknown'}`",
        "- every row is a measured run; a zero or tied row is a result (L1).",
        *_feedback_label_line(first.backend if first else ""),
    ]


def retry_comparison_rows(comparison: RetryRewriteComparison) -> list[tuple[str, ...]]:
    """Rows for the L16 retry row: weak-row recall@5 on/off and the gain (L7)."""
    header = ("language", "n_weak", "recall@5_off", "recall@5_on", "gain")
    rows: list[tuple[str, ...]] = [header]
    for language in (*[value.value for value in REQUIRED_LANGUAGES], "overall"):
        count = (
            len(comparison.subset.record_ids)
            if language == "overall"
            else comparison.subset.counts_by_language.get(language, 0)
        )
        rows.append(
            (
                language,
                str(count),
                _fmt(comparison.recall_off[language]),
                _fmt(comparison.recall_on[language]),
                f"{comparison.gains[language]:+.6f}",
            )
        )
    return rows


def retry_comparison_markdown(comparison: RetryRewriteComparison) -> str:
    """Render the retry verdict table with its own labels and verdict (L1/L16)."""
    composition = ", ".join(
        f"{language} {count}"
        for language, count in sorted(comparison.subset.counts_by_language.items())
    )
    header = [
        "# retry_rewrite: single pass vs retry-on",
        "",
        *_comparison_labels([comparison.single_pass]),
        f"- weak-evidence definition: answerable row with single-pass confidence "
        f"< {comparison.subset.threshold}; composition: {composition or 'none'} (L7)",
        f"- L16 verdict: `{comparison.verdict.value}` (zero or negative overall gain removes)",
        "- scope: this verdict is for the labelled offline backend above only; the "
        "rewrite transport there echoes its prompt, so a live-provider re-run is "
        "required before treating the verdict as production evidence (opt-in, parked).",
        "",
        _markdown_table(retry_comparison_rows(comparison)),
        "",
    ]
    return "\n".join(header)


def write_retry_comparison(comparison: RetryRewriteComparison, report_dir: Path) -> list[Path]:
    """Write both variant tables and the retry comparison pair."""
    report_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for result in (comparison.single_pass, comparison.retry_on):
        paths.extend(write_variant_tables(result, report_dir))
    markdown = _write_text(
        report_dir / "retry-rewrite-comparison.md", retry_comparison_markdown(comparison)
    )
    csv_path = _write_text(
        report_dir / "retry-rewrite-comparison.csv", _csv_table(retry_comparison_rows(comparison))
    )
    return [*paths, markdown, csv_path]


def strategy_comparison_rows(comparison: StrategyComparison) -> list[tuple[str, ...]]:
    """Rows keyed by language, with both corpora and their recall@5 delta (L7)."""
    fixed = comparison.results["fixed_window"]
    sentence = comparison.results["sentence_boundary"]
    header = ("language", "corpus_fixed_window", "corpus_sentence_boundary", "gain")
    rows: list[tuple[str, ...]] = [header]
    for language in (*[value.value for value in REQUIRED_LANGUAGES], "overall"):
        left = fixed.overall if language == "overall" else fixed.scores_by_language[language]
        right = sentence.overall if language == "overall" else sentence.scores_by_language[language]
        rows.append(
            (
                language,
                _fmt(left.recall_at_k),
                _fmt(right.recall_at_k),
                f"{comparison.recall_gains[language]:+.4f}",
            )
        )
    return rows


def strategy_comparison_markdown(comparison: StrategyComparison) -> str:
    """Render the per-strategy corpus comparison, including a measured tie (L1)."""
    header = [
        "# Chunking strategy ablation: per-strategy corpora",
        "",
        *_comparison_labels(list(comparison.results.values())),
        "- corpora: the same fixture documents indexed once under fixed_window and "
        "once under sentence_boundary; each strategy queried against its own corpus.",
        "- chunk-id sets are distinct by construction; golden ids are translated into "
        "each corpus so no reference dangles (L12).",
        f"- differential effect: {'measured tie (no differential effect)' if comparison.tied else 'measured non-zero delta'}",
        "",
        _markdown_table(strategy_comparison_rows(comparison)),
        "",
    ]
    return "\n".join(header)


def write_strategy_comparison(comparison: StrategyComparison, report_dir: Path) -> list[Path]:
    """Write one labelled table pair per strategy plus the comparison pair."""
    report_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for strategy in CHUNKING_STRATEGIES:
        paths.extend(write_variant_tables(comparison.results[strategy], report_dir))
    markdown = _write_text(
        report_dir / "strategy-comparison.md", strategy_comparison_markdown(comparison)
    )
    csv_path = _write_text(
        report_dir / "strategy-comparison.csv", _csv_table(strategy_comparison_rows(comparison))
    )
    return [*paths, markdown, csv_path]


def write_latest(
    results: Sequence[RunResult], report_dir: Path, node_rows: Sequence[NodePurposeRow]
) -> Path:
    """Assemble the committed latest summary from the summary and default variant tables."""
    from uni_rag_eval.domain.variant import DEFAULT_VARIANT

    default = next(
        (result for result in results if result.context.variant_name == DEFAULT_VARIANT.name),
        results[0],
    )
    text = "\n".join(
        [
            summary_markdown(results, node_rows).rstrip("\n"),
            "",
            "---",
            "",
            variant_table_markdown(default).rstrip("\n"),
            "",
        ]
    )
    return _write_text(report_dir / "latest.md", text)
