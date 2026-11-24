"""End-to-end pipeline specs under deterministic fakes (L4, L5, L13)."""

from __future__ import annotations

import pytest

from packages.retrieval.tests.fixtures.corpus import (
    FIXED_TIME,
    WEAK_QUERY,
    build_corpus,
    golden_queries,
    golden_query,
    indexed_store,
    make_pipeline,
    settings_for_tests,
)
from packages.retrieval.tests.fixtures.sources import CorpusChunkSource
from uni_rag_core import (
    FakeClock,
    FakeEmbedder,
    FakeLLM,
    FakeReranker,
    Language,
    Query,
    RetrievalError,
    ScoredChunk,
    ValidationError,
)
from uni_rag_retrieval.domain.fusion import SearchMode
from uni_rag_retrieval.service import RetrievalPipeline, maybe_boost

_CORPUS = build_corpus()
_BY_ID = {chunk.chunk_id: chunk for chunk in _CORPUS}


def test_pipeline_is_byte_deterministic_under_fakes() -> None:
    pipeline = make_pipeline()
    query = golden_query(golden_queries()[0])
    assert pipeline.run(query).model_dump_json() == pipeline.run(query).model_dump_json()


@pytest.mark.parametrize("row", golden_queries(), ids=lambda row: row["id"])
def test_golden_answers_carry_resolving_citations(row: dict) -> None:
    query = golden_query(row)
    answer = make_pipeline().run(query)

    assert answer.abstained is False
    assert answer.query_id == row["id"]
    assert answer.language is Language(row["language"])
    assert answer.citations
    cited_docs = {citation.doc_id for citation in answer.citations}
    assert set(row["expected_doc_ids"]) <= cited_docs
    assert answer.citations[0].doc_id in row["expected_doc_ids"]

    snippet_text = " ".join(citation.snippet for citation in answer.citations)
    assert row["expected_answer_snippet"] in snippet_text

    for citation in answer.citations:
        chunk = _BY_ID[citation.chunk_id]
        assert citation.doc_id == chunk.doc_id
        assert citation.source_url == chunk.source_url
        assert citation.page == chunk.page
        assert chunk.last_crawled.isoformat() in answer.text
        assert chunk.source_url in answer.text


def test_weak_evidence_abstains_with_next_step_and_no_fabrication() -> None:
    answer = make_pipeline().run(WEAK_QUERY)
    assert answer.abstained is True
    assert answer.citations == []
    assert answer.images == []
    assert answer.confidence == 0.0
    assert "Next step" in answer.text
    assert "2026" not in answer.text
    assert "@" not in answer.text


@pytest.mark.parametrize(
    ("text", "language", "next_step_marker"),
    [
        ("What is the parking fee?", Language.EN, "Next step"),
        ("پارکنگ کی فیس کتنی ہے؟", Language.UR, "اگلا قدم"),
        ("Parking ka fee kitna hai?", Language.ROMAN_URDU, "Agla qadam"),
    ],
)
def test_abstention_keeps_language_parity(
    text: str, language: Language, next_step_marker: str
) -> None:
    query = Query(query_id="force-abstain", text=text, language=language)
    answer = make_pipeline(abstention_threshold=1.0).run(query)

    assert answer.abstained is True
    assert answer.language is language
    assert next_step_marker in answer.text
    assert answer.citations == []


def test_lexical_only_axis_can_recall_chunks_dense_misses() -> None:
    query = golden_query(golden_queries()[0])
    source = CorpusChunkSource(_CORPUS)

    dense = make_pipeline(corpus=[], search_mode=SearchMode.DENSE).run(query)
    lexical = make_pipeline(corpus=[], search_mode=SearchMode.LEXICAL, chunk_source=source).run(
        query
    )

    assert dense.abstained is True
    assert lexical.citations
    assert lexical.citations[0].doc_id == "doc-cs101-outline"


def test_empty_llm_completion_raises_a_typed_error() -> None:
    class EmptyLLM:
        def complete(self, prompt: str, *, system: str | None = None) -> str:
            return "   "

    pipeline = RetrievalPipeline(
        settings=settings_for_tests(),
        embedder=FakeEmbedder(dimension=16),
        vector_store=indexed_store(),
        reranker=FakeReranker(),
        llm=EmptyLLM(),
        clock=FakeClock(FIXED_TIME),
    )
    with pytest.raises(RetrievalError):
        pipeline.run(golden_query(golden_queries()[0]))


def test_answer_images_are_real_image_refs_from_the_store() -> None:
    answer = make_pipeline().run(golden_query(golden_queries()[0]))
    assert [image.ref_id for image in answer.images] == ["images/doc-cs101-outline/p1.png"]
    assert answer.images[0].page == 1
    assert answer.images[0].source_url == _BY_ID["chunk-cs101-instructor"].source_url


@pytest.mark.parametrize(
    "search_mode",
    [SearchMode.DENSE, SearchMode.LEXICAL, SearchMode.HYBRID],
)
def test_named_search_mode_axis_is_injected(search_mode: SearchMode) -> None:
    pipeline = make_pipeline(search_mode=search_mode)
    answer = pipeline.run(golden_query(golden_queries()[0]))
    assert answer.abstained is False
    assert answer.citations


@pytest.mark.parametrize("rerank_enabled", [True, False])
def test_named_rerank_axis_is_injected(rerank_enabled: bool) -> None:
    pipeline = make_pipeline(rerank_enabled=rerank_enabled)
    assert pipeline.run(golden_query(golden_queries()[0])).citations


@pytest.mark.parametrize("freshness_enabled", [True, False])
def test_named_freshness_axis_is_injected(freshness_enabled: bool) -> None:
    pipeline = make_pipeline(freshness_boost_enabled=freshness_enabled)
    assert pipeline.run(golden_query(golden_queries()[0])).citations


def test_freshness_axis_changes_a_equal_relevance_fixture_pair() -> None:
    chunks = [chunk for chunk in _CORPUS if chunk.chunk_id.startswith("chunk-fresh")]
    ranked = [
        ScoredChunk(chunk=chunk, score=0.7, rank=rank) for rank, chunk in enumerate(chunks, 1)
    ]

    unboosted = maybe_boost(ranked, enabled=False, now=FIXED_TIME, half_life_days=365.0)
    boosted = maybe_boost(ranked, enabled=True, now=FIXED_TIME, half_life_days=365.0)

    assert [item.chunk.chunk_id for item in unboosted] == ["chunk-fresh-new", "chunk-fresh-old"]
    assert [item.chunk.chunk_id for item in boosted] == ["chunk-fresh-new", "chunk-fresh-old"]
    assert boosted[1].score < unboosted[1].score == 0.7


def test_maybe_boost_without_a_clock_value_returns_input_unmodified() -> None:
    ranked = [ScoredChunk(chunk=_CORPUS[0], score=0.5, rank=1)]
    assert maybe_boost(ranked, enabled=True, now=None, half_life_days=365.0) == ranked


def test_pipeline_rejects_invalid_ablation_configuration() -> None:
    with pytest.raises(ValidationError):
        RetrievalPipeline(
            settings=settings_for_tests(),
            embedder=FakeEmbedder(dimension=16),
            vector_store=indexed_store(),
            reranker=FakeReranker(),
            llm=FakeLLM(),
            clock=FakeClock(FIXED_TIME),
            rrf_k=0,
        )


def test_default_top_k_comes_from_typed_settings() -> None:
    query = Query(
        query_id="default-k",
        text="Who is the instructor for CS-101?",
        language=Language.EN,
        top_k=0,
    )
    answer = make_pipeline(default_top_k=10).run(query)
    assert len(answer.citations) <= 10
