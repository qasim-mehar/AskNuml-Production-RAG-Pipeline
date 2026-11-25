"""Lane F M3 specs: flag isolation, per-strategy corpora, pure verdict, determinism."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from eval_helpers import StubRetriever, load_fixture

from uni_rag_core import FakeClock
from uni_rag_eval.domain.golden import (
    chunks_for_strategy,
    golden_for_strategy,
    load_fixture_registry,
    load_golden_set,
    translate_expected_ids,
)
from uni_rag_eval.domain.variant import (
    CHUNKING_STRATEGIES,
    DEFAULT_VARIANT,
    FIXED_WINDOW,
    INTEGRATED_CHUNKING,
    RETRY_REWRITE_AXIS,
    SENTENCE_BOUNDARY,
    SearchMode,
    Verdict,
    build_variant,
    retry_rewrite_verdict,
    variant_matrix,
)
from uni_rag_eval.runner.ablation import (
    adr0010_strip_label,
    retry_comparison_markdown,
    strategy_comparison_markdown,
)
from uni_rag_eval.runner.harness import (
    RunContext,
    build_fake_pipeline,
    default_judge,
    recall_gain_on_subset,
    run_harness,
    weak_evidence_subset,
)
from uni_rag_eval.service.run import (
    run_retry_rewrite_comparison,
    run_strategy_comparison,
)

ROOT = Path(__file__).resolve().parents[3]


def _golden_and_registry() -> tuple[object, object]:
    golden = load_golden_set(
        json.loads((ROOT / "eval/golden/golden.json").read_text(encoding="utf-8"))
    )
    registry = load_fixture_registry(
        json.loads((ROOT / "eval/golden/fixture-registry.json").read_text(encoding="utf-8"))
    )
    return golden, registry


def test_retry_axis_is_the_only_difference_between_on_and_off_variants() -> None:
    off = build_variant(SearchMode.HYBRID, True, False)
    on = build_variant(SearchMode.HYBRID, True, False, retry_rewrite=True)
    assert off.retry_rewrite is False
    assert on.retry_rewrite is True
    assert on.model_copy(update={"retry_rewrite": False, "name": off.name}) == off
    assert on.name.endswith("-retry-on")
    assert not off.name.endswith("-retry-on")
    assert DEFAULT_VARIANT.name == "hybrid-rerank-on-freshness-off-fixed_window+sentence_boundary"
    assert len(variant_matrix()) == 12
    assert len(variant_matrix(retry_rewrite_axis=RETRY_REWRITE_AXIS)) == 24


def test_verdict_is_pure_and_zero_or_negative_means_remove() -> None:
    assert retry_rewrite_verdict({"overall": 0.01}) is Verdict.KEEP
    assert retry_rewrite_verdict({"overall": 0.0}) is Verdict.REMOVE
    assert retry_rewrite_verdict({"overall": -0.02}) is Verdict.REMOVE
    gains = {"en": 99.0, "ur": -99.0, "overall": 0.0}
    assert retry_rewrite_verdict(gains) is retry_rewrite_verdict(dict(gains))
    with pytest.raises(Exception, match="finite"):
        retry_rewrite_verdict({"overall": float("nan")})


def test_per_strategy_corpora_have_distinct_chunk_ids_and_no_dangling_golden_ids() -> None:
    golden, registry = _golden_and_registry()
    fixed = chunks_for_strategy(registry, FIXED_WINDOW)
    sentence = chunks_for_strategy(registry, SENTENCE_BOUNDARY)
    fixed_ids = {chunk.chunk_id for chunk in fixed}
    sentence_ids = {chunk.chunk_id for chunk in sentence}
    assert fixed_ids.isdisjoint(sentence_ids), "strategies must not share an indexed chunk set"
    assert len(sentence_ids) > len(fixed_ids)
    indexed = {chunk.chunk_id: chunk for chunk in fixed}
    for chunk in fixed:
        assert indexed[chunk.chunk_id].content_hash == chunk.content_hash
    translated = golden_for_strategy(golden, registry, SENTENCE_BOUNDARY)
    assert translated.golden_id == golden.golden_id
    for before, after in zip(golden.records, translated.records, strict=True):
        expected = translate_expected_ids(registry, before.expected_chunk_ids, SENTENCE_BOUNDARY)
        assert list(after.expected_chunk_ids) == list(expected)
        assert set(expected) <= sentence_ids


def test_integrated_corpus_label_is_not_a_single_strategy() -> None:
    _, registry = _golden_and_registry()
    with pytest.raises(Exception, match="published chunking strategy"):
        chunks_for_strategy(registry, INTEGRATED_CHUNKING)


class _ConfidenceRetrieval:
    """Stub retrieval with an injected confidence, to drive the weak subset."""

    def __init__(self, confidence: float) -> None:
        self._inner = StubRetriever(load_fixture("stub-answers.json")["answers"])
        self._confidence = confidence

    def __call__(self, query: object):
        answer = self._inner(query)
        return answer.model_copy(update={"confidence": self._confidence})


def _stub_run(confidence: float) -> object:
    golden = load_golden_set(load_fixture("synthetic-golden.json"))
    context = RunContext(
        run_id="weak-subset-test",
        backend="stub",
        corpus="synthetic",
        variant_name="stub",
        chunking_strategy=INTEGRATED_CHUNKING,
        golden_id=golden.golden_id,
        top_k=3,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    return run_harness(golden, _ConfidenceRetrieval(confidence), default_judge(), context)


def test_weak_subset_and_gain_are_labelled_by_language_and_pure() -> None:
    golden = load_golden_set(load_fixture("synthetic-golden.json"))
    off = _stub_run(confidence=0.1)
    on = _stub_run(confidence=0.9)
    subset = weak_evidence_subset(golden, off, threshold=0.35)
    assert subset.counts_by_language == {"en": 2, "roman_urdu": 1}
    assert "s2" not in subset.record_ids, "an abstain row has no measurable recall gain"
    gains = recall_gain_on_subset(subset, off, on)
    assert set(gains) == {"en", "ur", "roman_urdu", "overall"}
    assert gains == recall_gain_on_subset(subset, off, on)
    assert gains["ur"] == 0.0


def _fake_factory(variant: object):
    chunks = chunks_for_strategy(_golden_and_registry()[1], FIXED_WINDOW)
    return build_fake_pipeline(chunks, variant=variant, clock=FakeClock())


def test_comparison_tables_carry_backend_and_adr_labels_and_are_deterministic() -> None:
    golden, registry = _golden_and_registry()
    backend = "fake|strip_source=in-memory"
    first = run_retry_rewrite_comparison(
        golden, registry, _fake_factory, backend=backend, corpus="fixture", clock="fake"
    )
    second = run_retry_rewrite_comparison(
        golden, registry, _fake_factory, backend=backend, corpus="fixture", clock="fake"
    )
    assert retry_comparison_markdown(first) == retry_comparison_markdown(second)
    table = retry_comparison_markdown(first)
    assert backend in table
    assert adr0010_strip_label(backend) in table
    for language in ("en", "ur", "roman_urdu", "overall"):
        assert f"| {language} |" in table

    strategy_first = run_strategy_comparison(
        golden, registry, _fake_factory, backend=backend, clock="fake"
    )
    strategy_second = run_strategy_comparison(
        golden, registry, _fake_factory, backend=backend, clock="fake"
    )
    assert strategy_comparison_markdown(strategy_first) == strategy_comparison_markdown(
        strategy_second
    )
    assert set(strategy_first.results) == set(CHUNKING_STRATEGIES)
    assert strategy_comparison_markdown(strategy_first).count("| en |") >= 1
