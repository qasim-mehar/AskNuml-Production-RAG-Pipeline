"""Lane F F5 specs: one subset rule, labelled node rows, frozen baselines (L1/L16)."""

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from uni_rag_core import Answer, Citation, FakeClock, Language, Query
from uni_rag_eval.domain.feedback import (
    FEEDBACK_BACKEND_MARKER,
    FEEDBACK_PROVENANCE,
    assert_offline_feedback_label,
    feedback_backend_label,
)
from uni_rag_eval.domain.golden import (
    chunks_for_strategy,
    chunks_from_registry,
    golden_for_strategy,
    load_fixture_registry,
    load_golden_set,
    validate_golden_set,
)
from uni_rag_eval.domain.variant import (
    FIXED_WINDOW,
    NODE_VARIANTS,
    SENTENCE_BOUNDARY,
    NodeVariant,
    SearchMode,
    Verdict,
    build_variant,
    l16_verdict,
    variant_matrix,
)
from uni_rag_eval.runner.ablation import node_comparison_markdown, write_node_comparison
from uni_rag_eval.runner.harness import (
    INCLUDE_FEEDBACK_SUBSET_RULE,
    build_fake_pipeline,
    weak_evidence_subset,
)
from uni_rag_eval.service.run import main, run_f5_comparisons

ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = ROOT / "eval/golden/baseline.json"
BASELINE_FEEDBACK_PATH = ROOT / "eval/golden/baseline-feedback.json"
# Byte-pinned by test_gate.py: the curated baseline must never move (L1/L4).
PINNED_BASELINE_SHA256 = "0a4ab373a255f085063949c7fcc62ec4f75c06f5205eebfb1703ed7177049813"
BACKEND = feedback_backend_label("fake|live=False|strip_source=in-memory")
_FORBIDDEN_LIVE_CLAIMS = ("live_feedback=true", "live feedback", "feedback=live", "feedback=real")


def _inputs() -> tuple[object, object]:
    golden = load_golden_set(
        json.loads((ROOT / "eval/golden/golden-feedback.json").read_text(encoding="utf-8"))
    )
    registry = load_fixture_registry(
        json.loads((ROOT / "eval/golden/fixture-registry.json").read_text(encoding="utf-8"))
    )
    return golden, registry


def _fake_factory(variant: object):
    _, registry = _inputs()
    chunks = chunks_for_strategy(registry, FIXED_WINDOW)
    return build_fake_pipeline(chunks, variant=variant, clock=FakeClock())


def _comparisons() -> object:
    golden, registry = _inputs()
    return run_f5_comparisons(
        golden,
        registry,
        _fake_factory,
        backend=BACKEND,
        corpus="fixture-corpus-v1-integrated",
        clock="FakeClock(2026-01-01T00:00:00+00:00)",
    )


def _normalized_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_node_axis_is_the_only_difference_between_single_pass_and_node_on() -> None:
    base = build_variant(SearchMode.HYBRID, True, False)
    assert base.node_variant is NodeVariant.SINGLE_PASS
    assert not base.name.endswith("-on")
    for node in NODE_VARIANTS:
        on = build_variant(SearchMode.HYBRID, True, False, node_variant=node)
        assert on.node_variant is node
        assert on.name.endswith(f"-node={node.value}-on")
        assert (
            on.model_copy(update={"node_variant": NodeVariant.SINGLE_PASS, "name": base.name})
            == base
        )
    assert len(variant_matrix()) == 12, "the baseline matrix must not grow"


def test_l16_verdict_is_pure_and_zero_or_negative_means_remove() -> None:
    assert l16_verdict({"overall": 0.01}) is Verdict.KEEP
    assert l16_verdict({"overall": 0.0}) is Verdict.REMOVE
    assert l16_verdict({"overall": -0.01}) is Verdict.REMOVE
    gains = {"en": 99.0, "ur": -99.0, "overall": 0.0}
    assert l16_verdict(gains) is l16_verdict(dict(gains))
    with pytest.raises(Exception, match="finite"):
        l16_verdict({})


class _EchoLLM:
    """Offline transport stand-in: it echoes the prompt and supplies no node value."""

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        return f"google-genai[offline]: {prompt}"


def test_prompt_echo_cannot_supply_a_node_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    composition = importlib.import_module("eval.composition")
    assert (
        composition._node_marker(
            "google-genai[offline]: CLARIFY_DOC_ID=doc-cs101-outline", "CLARIFY_DOC_ID="
        )
        is None
    )
    assert (
        composition._node_marker("CLARIFY_DOC_ID=doc-cs101-outline", "CLARIFY_DOC_ID=")
        == "doc-cs101-outline"
    )
    cited = Citation(
        chunk_id="doc-cs101-outline::c01",
        doc_id="doc-cs101-outline",
        source_url="https://example.test/outline",
        snippet="outline",
    )
    query = Query(query_id="q-echo", text="Where is the outline?", language=Language.EN, top_k=5)
    for node in NODE_VARIANTS:
        abstained = node is NodeVariant.CLARIFY
        answer = Answer(
            answer_id="a-echo",
            query_id=query.query_id,
            text="echoed answer",
            citations=[] if abstained else [cited],
            abstained=abstained,
            confidence=0.1,
            language=Language.EN,
        )
        wrapper = composition.MeasuredNode(
            lambda _query, _answer=answer: _answer,
            llm=_EchoLLM(),
            node=node,
            top_k=5,
        )
        assert wrapper(query) == answer
    for comparison in _comparisons().nodes.values():
        assert all(abs(gain) < 1e-12 for gain in comparison.gains.values())
        assert comparison.verdict is Verdict.REMOVE


def test_subset_rule_is_consistent_across_all_measured_nodes() -> None:
    comparisons = _comparisons()
    subsets = [comparison.subset for comparison in comparisons.nodes.values()]
    assert len(subsets) == len(NODE_VARIANTS)
    assert all(subset == subsets[0] for subset in subsets)
    assert all(subset.subset_rule == INCLUDE_FEEDBACK_SUBSET_RULE for subset in subsets)


def test_feedback_derived_rows_follow_one_declared_include_rule() -> None:
    golden, _ = _inputs()
    derived = {record.id for record in golden.records if record.provenance == FEEDBACK_PROVENANCE}
    assert len(derived) == 6
    assert len(golden.records) == 36
    single_pass = _comparisons().single_pass
    weak_run = replace(
        single_pass,
        traces=tuple(replace(trace, confidence=0.0) for trace in single_pass.traces),
    )
    included = weak_evidence_subset(golden, weak_run)
    excluded = weak_evidence_subset(golden, weak_run, include_feedback_derived=False)
    assert derived <= included.record_ids
    assert derived.isdisjoint(excluded.record_ids)
    assert included.subset_rule == INCLUDE_FEEDBACK_SUBSET_RULE
    assert excluded.subset_rule != included.subset_rule


def test_no_dangling_ids_in_curated_extended_or_per_strategy_corpora() -> None:
    golden, registry = _inputs()
    root = ROOT
    verified = {doc.source_path for doc in registry.documents if (root / doc.source_path).is_file()}
    validate_golden_set(golden, registry, verified)
    curated_ids = {chunk.chunk_id for chunk in chunks_from_registry(registry)}
    extended_ids = {record.id for record in golden.records}
    assert len(extended_ids) == len(golden.records)
    for record in golden.records:
        assert set(record.expected_chunk_ids) <= curated_ids
    for strategy in (FIXED_WINDOW, SENTENCE_BOUNDARY):
        strategy_ids = {chunk.chunk_id for chunk in chunks_for_strategy(registry, strategy)}
        translated = golden_for_strategy(golden, registry, strategy)
        assert translated.golden_id == golden.golden_id
        for record in translated.records:
            assert set(record.expected_chunk_ids) <= strategy_ids
    assert {chunk.chunk_id for chunk in chunks_from_registry(registry)} == curated_ids


def test_node_reports_are_label_pure_and_carry_the_full_chain(tmp_path: Path) -> None:
    comparisons = _comparisons()
    assert_offline_feedback_label(BACKEND)
    for node, comparison in comparisons.nodes.items():
        assert (
            comparison.single_pass.context.backend == comparison.node_on.context.backend == BACKEND
        )
        assert "live=False" in BACKEND
        assert FEEDBACK_BACKEND_MARKER in BACKEND
        markdown = node_comparison_markdown(comparison)
        assert "live=False" in markdown
        assert FEEDBACK_BACKEND_MARKER in markdown
        assert INCLUDE_FEEDBACK_SUBSET_RULE in markdown
        assert "NOT live user feedback" in markdown
        lowered = markdown.lower()
        assert not any(claim in lowered for claim in _FORBIDDEN_LIVE_CLAIMS)
        assert "prompt echoes" in markdown or "echoes its" in markdown
        paths = write_node_comparison(comparison, tmp_path)
        assert {path.name for path in paths} == {
            f"{node.value}-comparison.md",
            f"{node.value}-comparison.csv",
        }


def test_every_node_report_has_en_ur_roman_urdu_and_overall_rows() -> None:
    comparisons = _comparisons()
    for comparison in comparisons.nodes.values():
        markdown = node_comparison_markdown(comparison)
        rows = [
            line for line in markdown.splitlines() if line.startswith("| ") and "---" not in line
        ]
        languages = [line.split("|")[1].strip() for line in rows[1:]]
        assert languages == ["en", "ur", "roman_urdu", "overall"]
        for language in languages:
            assert f"| {language} |" in markdown
        assert set(comparison.gains) == {"en", "ur", "roman_urdu", "overall"}


def test_f5_rerun_leaves_both_baselines_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The run-only composition lives at the workspace root, outside the shipped
    # eval package; pytest's rootdir for these specs is packages/eval (L14).
    monkeypatch.syspath_prepend(str(ROOT))
    before_curated = _normalized_sha256(BASELINE_PATH)
    before_extended = _normalized_sha256(BASELINE_FEEDBACK_PATH)
    assert before_curated == PINNED_BASELINE_SHA256
    exit_code = main(
        [
            "--mode",
            "f5",
            "--golden",
            str(ROOT / "eval/golden/golden-feedback.json"),
            "--feedback",
            str(ROOT / "eval/golden/feedback-fixture.json"),
            "--pipeline-factory",
            "eval.composition:build_pipeline",
            "--backend",
            "fetcher=fake|parser=docling|chunking=strategies|vector=qdrant_local|objects=fake"
            "|metadata=none|clock=fake|embedder=google_genai|reranker=fake|llm=google_genai"
            "|live=False|parser_engine=fixture-reader|adapters=real-offline|ADR0010-strip"
            "|strip_source=in-memory|feedback=derived|feedback_source=fixture-transcript"
            "|live_feedback=False",
            "--corpus",
            "fixture-corpus-v1-integrated",
            "--clock",
            "FakeClock(2026-01-01T00:00:00+00:00)",
            "--reports",
            str(tmp_path),
            "--baseline",
            str(BASELINE_FEEDBACK_PATH),
        ]
    )
    assert exit_code == 0
    assert _normalized_sha256(BASELINE_PATH) == before_curated
    assert _normalized_sha256(BASELINE_FEEDBACK_PATH) == before_extended
    for node in NODE_VARIANTS:
        markdown = (tmp_path / f"{node.value}-comparison.md").read_text(encoding="utf-8")
        assert "- L16 verdict: `REMOVE`" in markdown
        assert "| overall | 24 | 0.0000 | 0.0000 | +0.000000 |" in markdown
        assert (tmp_path / f"{node.value}-comparison.csv").is_file()
