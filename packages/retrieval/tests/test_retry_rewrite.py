"""retry_rewrite specs: capped loop, provenance, abstention, L7 parity, flag-off identity.

Fixtures first; all behaviour is pinned under deterministic fakes (L4, L12).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from packages.retrieval.tests.fixtures.corpus import (
    FIXED_TIME,
    golden_queries,
    golden_query,
    indexed_store,
    settings_for_tests,
)
from packages.retrieval.tests.fixtures.retry import (
    STILL_WEAK_REWRITE,
    STRONG_REWRITE,
    WEAK_QUERY,
    WEAK_QUERY_BY_LANGUAGE,
    ScriptedRewriteLLM,
    make_outcome,
    make_request,
    make_retry_pipeline,
    run_linear_reference,
    stale_chunk,
)
from uni_rag_core import (
    Chunk,
    FakeClock,
    FakeEmbedder,
    FakeReranker,
    Language,
    Query,
    RetrievalError,
    ScoredChunk,
    ValidationError,
)
from uni_rag_retrieval.domain.prompts import build_rewrite_prompt
from uni_rag_retrieval.domain.router import FilterSet
from uni_rag_retrieval.graph import NODE_REGISTRY, NODE_SPECS, retry_rewrite_node
from uni_rag_retrieval.service import (
    RetrievalPipeline,
    RetryRewriteConfig,
    RetryRewriteRequest,
    route_query,
)

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "uni_rag_retrieval"


class MarkerReranker:
    """Score 1.0 only when the query carries the rewrite marker, else 0.0."""

    def __init__(self, marker: str) -> None:
        self._marker = marker

    def rerank(self, query: str, candidates: Sequence[Chunk]) -> list[ScoredChunk]:
        """Return deterministic scores so the rerank axis is observable."""
        score = 1.0 if self._marker in query else 0.0
        return [
            ScoredChunk(chunk=chunk, score=score, rank=rank)
            for rank, chunk in enumerate(candidates, start=1)
        ]


def test_capped_loop_runs_exactly_the_injected_number_of_attempts() -> None:
    outcome, llm = make_outcome(rewrites=(STILL_WEAK_REWRITE,), iterations=2)

    assert outcome.attempts == 2
    assert llm.rewrite_calls == 2
    assert outcome.rewrite_history == (STILL_WEAK_REWRITE, STILL_WEAK_REWRITE)
    assert outcome.query_text == STILL_WEAK_REWRITE
    assert outcome.strong is False
    assert make_outcome(rewrites=(STILL_WEAK_REWRITE,), iterations=2)[0] == outcome


def test_successful_rewrite_stops_early_and_is_deterministic() -> None:
    outcome, llm = make_outcome(rewrites=(STRONG_REWRITE, STILL_WEAK_REWRITE), iterations=2)

    assert outcome.attempts == 1
    assert llm.rewrite_calls == 1
    assert outcome.rewrite_history == (STRONG_REWRITE,)
    assert outcome.strong is True
    assert outcome.top_score >= 0.35
    assert outcome.scored[0].chunk.chunk_id == "chunk-weak-parking"


def test_successful_rewrite_yields_a_cited_answer_with_native_last_crawled() -> None:
    llm = ScriptedRewriteLLM((STRONG_REWRITE,))

    answer = make_retry_pipeline(llm=llm).run(WEAK_QUERY)

    assert answer.abstained is False
    assert answer.citations
    assert answer.citations[0].chunk_id == "chunk-weak-parking"
    assert answer.citations[0].last_crawled == FIXED_TIME
    assert answer.text == "Fake answer."
    assert "Sources (last crawled" not in answer.text
    assert answer.citations[0].source_url not in answer.text
    assert llm.rewrite_prompts == [build_rewrite_prompt(route_query(WEAK_QUERY).normalized_text)]


def test_a_still_weak_rewrite_abstains_with_a_structured_next_step() -> None:
    llm = ScriptedRewriteLLM((STILL_WEAK_REWRITE,))

    answer = make_retry_pipeline(llm=llm, iterations=2).run(WEAK_QUERY)

    assert answer.abstained is True
    assert answer.citations == []
    assert answer.images == []
    assert answer.next_step and "department office" in answer.next_step
    assert answer.abstention_reason
    assert "Next step" not in answer.text
    assert "2026" not in answer.text and "@" not in answer.text
    assert llm.rewrite_calls == 2


def test_retry_respects_the_freshness_axis_and_does_not_mask_stale_evidence() -> None:
    chunk = stale_chunk()
    llm = ScriptedRewriteLLM(("alpha beta gamma",))

    boosted = make_retry_pipeline(llm=llm, corpus=[chunk]).run(WEAK_QUERY)
    unboosted = make_retry_pipeline(llm=llm, corpus=[chunk], freshness_boost_enabled=False).run(
        WEAK_QUERY
    )

    assert boosted.abstained is True
    assert boosted.citations == []
    assert boosted.next_step
    assert unboosted.abstained is False
    assert unboosted.confidence == pytest.approx(1.0)


def test_retry_keeps_the_rerank_off_ablation() -> None:
    chunk = stale_chunk(text="nothing relevant here")
    llm = ScriptedRewriteLLM(("alpha beta gamma",))
    reranker = MarkerReranker("alpha")

    rerank_on = make_retry_pipeline(
        llm=llm, corpus=[chunk], reranker=reranker, freshness_boost_enabled=False
    ).run(WEAK_QUERY)
    rerank_off = make_retry_pipeline(
        llm=llm,
        corpus=[chunk],
        reranker=reranker,
        rerank_enabled=False,
        freshness_boost_enabled=False,
    ).run(WEAK_QUERY)

    assert rerank_on.abstained is False
    assert rerank_off.abstained is True
    assert rerank_off.citations == []


@pytest.mark.parametrize(("query", "rewrite", "marker"), WEAK_QUERY_BY_LANGUAGE)
def test_rewrite_preserves_language_and_does_not_override_the_router(
    query: Query, rewrite: str, marker: str
) -> None:
    llm = ScriptedRewriteLLM((rewrite,))

    answer = make_retry_pipeline(llm=llm).run(query)
    outcome, _ = make_outcome(query=query, rewrites=(rewrite,))

    decision = route_query(query)
    assert decision.normalized_text in llm.rewrite_prompts[0]
    assert marker in outcome.rewrite_history[0]
    assert "<<RETRIEVED_DATA" not in llm.rewrite_prompts[0]
    assert answer.language is query.language


def test_flag_off_output_is_byte_identical_to_the_linear_path() -> None:
    spy = ScriptedRewriteLLM((STRONG_REWRITE,))
    pipeline = RetrievalPipeline(
        settings=settings_for_tests(),
        embedder=FakeEmbedder(dimension=16),
        vector_store=indexed_store(),
        reranker=FakeReranker(),
        llm=spy,
        clock=FakeClock(FIXED_TIME),
    )

    for query in (WEAK_QUERY, golden_query(golden_queries()[0])):
        assert (
            pipeline.run(query).model_dump_json()
            == run_linear_reference(query, llm=spy).model_dump_json()
        )
    assert spy.rewrite_calls == 0


def test_registry_has_one_live_retry_node_and_three_scaffolded_nodes() -> None:
    assert NODE_REGISTRY["retry_rewrite"] is retry_rewrite_node
    assert NODE_SPECS["retry_rewrite"].implemented
    assert "recall@k gain vs single pass at k=5" in NODE_SPECS["retry_rewrite"].eval_row
    assert [name for name, spec in NODE_SPECS.items() if not spec.implemented] == [
        "clarify",
        "multihop",
        "checkpoint_followup",
    ]


def test_graph_node_is_a_thin_wrapper_over_the_plain_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    seen: list[RetryRewriteRequest] = []
    monkeypatch.setattr(
        "uni_rag_retrieval.graph.nodes.retry_rewrite_service",
        lambda request: seen.append(request) or sentinel,
    )
    request = RetryRewriteRequest(
        query_text="weak query",
        scored=[],
        llm=ScriptedRewriteLLM(()),
        embedder=FakeEmbedder(dimension=16),
        vector_store=indexed_store(),
        reranker=FakeReranker(),
        filters=FilterSet(),
        language=Language.EN,
        top_k=5,
        threshold=0.35,
    )

    assert retry_rewrite_node(request) is sentinel
    assert seen == [request]


def test_framework_imports_stay_outside_graph_and_adapters() -> None:
    for path in _SOURCE_ROOT.rglob("*.py"):
        if set(path.relative_to(_SOURCE_ROOT).parts) & {"graph", "adapters"}:
            continue
        source = path.read_text(encoding="utf-8")
        assert "langgraph" not in source, str(path)
        assert "langchain" not in source, str(path)


def test_a_non_positive_iteration_cap_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RetryRewriteConfig(max_iterations=0)
    with pytest.raises(ValidationError):
        RetrievalPipeline(
            settings=settings_for_tests(),
            embedder=FakeEmbedder(dimension=16),
            vector_store=indexed_store(),
            reranker=FakeReranker(),
            llm=ScriptedRewriteLLM(()),
            clock=FakeClock(FIXED_TIME),
            retry_rewrite_iterations=0,
        )


def test_an_empty_rewrite_is_a_typed_retrieval_error() -> None:
    request = make_request(rewrites=("",))
    with pytest.raises(RetrievalError):
        from uni_rag_retrieval.service import retry_rewrite

        retry_rewrite(request)
