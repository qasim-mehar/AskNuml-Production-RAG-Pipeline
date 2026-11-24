"""Deterministic fixtures for the capped retry-rewrite loop (L4, L12).

The weak query has no token overlap with the fixture corpus. A scripted LLM
returns a fixed rewrite whose terms *do* overlap one chunk, so the second
search is strong; a second script keeps the retrieval weak to exercise the
abstention branch. No network, SDK or wall-clock value is involved.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from packages.retrieval.tests.fixtures.corpus import (
    FIXED_TIME,
    indexed_store,
    settings_for_tests,
)
from uni_rag_core import (
    LLM,
    Answer,
    Chunk,
    DocType,
    FakeClock,
    FakeEmbedder,
    FakeReranker,
    Language,
    Query,
    Reranker,
    Settings,
)
from uni_rag_retrieval.domain.fusion import SearchMode
from uni_rag_retrieval.domain.prompts import ANSWER_SYSTEM, REWRITE_SYSTEM
from uni_rag_retrieval.service import (
    RetrievalPipeline,
    RetryRewriteConfig,
    RetryRewriteRequest,
    build_abstention,
    hybrid_search,
    maybe_boost,
    rerank_candidates,
    retry_rewrite,
    route_query,
    synthesize_answer,
)
from uni_rag_retrieval.service.retry_rewrite import RewriteOutcome

WEAK_QUERY = Query(
    query_id="retry-weak",
    text="What is the parking fee for students?",
    language=Language.EN,
)
STRONG_REWRITE = "campus map office hours"
STILL_WEAK_REWRITE = "parking fee unknown"
STALE_TIME = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)


def stale_chunk(*, text: str = "alpha beta gamma") -> Chunk:
    """Return a two-year-old single chunk for freshness-ablation specs (L4)."""
    return Chunk(
        chunk_id="chunk-stale",
        doc_id="doc-stale",
        source_url="https://example.edu/stale",
        heading_path=["stale"],
        content_hash="hash-chunk-stale",
        last_crawled=STALE_TIME,
        doc_type=DocType.WEB_PAGE,
        version="1",
        text=text,
    )


WEAK_QUERY_BY_LANGUAGE: tuple[tuple[Query, str, str], ...] = (
    (WEAK_QUERY, STRONG_REWRITE, "map"),
    (
        Query(
            query_id="retry-ur",
            text="پارکنگ کی فیس کتنی ہے؟",
            language=Language.UR,
        ),
        "CS-101 کے انسٹرکٹر ڈاکٹر عائشہ خان",
        "انسٹرکٹر",
    ),
    (
        Query(
            query_id="retry-roman",
            text="Parking fee kya hai aur kaise?",
            language=Language.ROMAN_URDU,
        ),
        STRONG_REWRITE,
        "map",
    ),
)


class ScriptedRewriteLLM:
    """Return queued rewrites for rewrite prompts and a fixed answer otherwise.

    Records every prompt so tests can prove the flag-off path never calls the
    rewrite stage and that the rewrite prompt carries query text only (L4, L7).
    """

    def __init__(self, rewrites: Sequence[str], *, answer: str = "Fake answer.") -> None:
        self._rewrites = tuple(rewrites)
        self._answer = answer
        self.rewrite_prompts: list[str] = []
        self.answer_prompts: list[str] = []

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return the next queued rewrite, or a stable answer completion."""
        if system == REWRITE_SYSTEM:
            self.rewrite_prompts.append(prompt)
            index = min(len(self.rewrite_prompts) - 1, len(self._rewrites) - 1)
            return self._rewrites[index]
        if system == ANSWER_SYSTEM:
            self.answer_prompts.append(prompt)
            return self._answer
        return self._answer

    @property
    def rewrite_calls(self) -> int:
        """Return how many rewrite completions were requested."""
        return len(self.rewrite_prompts)


def make_retry_pipeline(
    *,
    rewrites: Sequence[str] = (STRONG_REWRITE,),
    iterations: int = 1,
    threshold: float = 0.35,
    llm: LLM | None = None,
    corpus: list[Chunk] | None = None,
    reranker: Reranker | None = None,
    rerank_enabled: bool = True,
    freshness_boost_enabled: bool = True,
) -> RetrievalPipeline:
    """Build a fully faked pipeline with the retry flag on (L4)."""
    return RetrievalPipeline(
        settings=settings_for_tests(abstention_threshold=threshold),
        embedder=FakeEmbedder(dimension=16),
        vector_store=indexed_store(corpus),
        reranker=reranker if reranker is not None else FakeReranker(),
        llm=llm if llm is not None else ScriptedRewriteLLM(rewrites),
        clock=FakeClock(FIXED_TIME),
        rerank_enabled=rerank_enabled,
        freshness_boost_enabled=freshness_boost_enabled,
        retry_rewrite_enabled=True,
        retry_rewrite_iterations=iterations,
    )


def make_request(
    *,
    query: Query = WEAK_QUERY,
    rewrites: Sequence[str] = (STRONG_REWRITE,),
    iterations: int = 1,
    threshold: float = 0.35,
) -> RetryRewriteRequest:
    """Build a real, weak-retrieval request with fully faked ports."""
    settings: Settings = settings_for_tests(abstention_threshold=threshold)
    decision = route_query(query)
    top_k = query.top_k if query.top_k > 0 else settings.default_top_k
    candidates = hybrid_search(
        decision.normalized_text,
        embedder=FakeEmbedder(dimension=16),
        vector_store=indexed_store(),
        top_k=top_k,
        language=decision.language,
        filters=decision.filters,
        search_mode=SearchMode.HYBRID,
        candidate_multiplier=4,
        rrf_k=60,
    )
    scored = rerank_candidates(
        decision.normalized_text,
        candidates,
        reranker=FakeReranker(),
        enabled=True,
        language=decision.language,
    )
    return RetryRewriteRequest(
        query_text=decision.normalized_text,
        scored=scored,
        llm=ScriptedRewriteLLM(rewrites),
        embedder=FakeEmbedder(dimension=16),
        vector_store=indexed_store(),
        reranker=FakeReranker(),
        filters=decision.filters,
        language=decision.language,
        top_k=top_k,
        threshold=threshold,
        config=RetryRewriteConfig(max_iterations=iterations),
    )


def make_outcome(
    *,
    query: Query = WEAK_QUERY,
    rewrites: Sequence[str] = (STRONG_REWRITE,),
    iterations: int = 1,
    threshold: float = 0.35,
) -> tuple[RewriteOutcome, ScriptedRewriteLLM]:
    """Run the plain retry service against fakes and return its audit trail."""
    request = make_request(
        query=query, rewrites=rewrites, iterations=iterations, threshold=threshold
    )
    llm = request.llm
    assert isinstance(llm, ScriptedRewriteLLM)
    return retry_rewrite(request), llm


def run_linear_reference(query: Query, *, llm: LLM) -> Answer:
    """Compose the pre-node linear path from plain services for byte-identity.

    This is the exact sequence ``RetrievalPipeline.run`` used before the
    retry flag existed: route, filter/search, rerank, boost, abstain or answer.
    The ADR-0007 shims are already migrated here (native fields, no footer).
    """
    settings = settings_for_tests()
    decision = route_query(query)
    top_k = query.top_k if query.top_k > 0 else settings.default_top_k
    candidates = hybrid_search(
        decision.normalized_text,
        embedder=FakeEmbedder(dimension=16),
        vector_store=indexed_store(),
        top_k=top_k,
        language=decision.language,
        filters=decision.filters,
        search_mode=SearchMode.HYBRID,
        candidate_multiplier=4,
        rrf_k=60,
    )
    scored = rerank_candidates(
        decision.normalized_text,
        candidates,
        reranker=FakeReranker(),
        enabled=True,
        language=decision.language,
    )
    scored = maybe_boost(
        scored,
        enabled=True,
        now=FIXED_TIME,
        half_life_days=365.0,
    )
    top_score = scored[0].score if scored else 0.0
    if not scored or top_score < settings.abstention_threshold:
        return build_abstention(query, language=decision.language)
    return synthesize_answer(query, decision, scored, llm=llm, top_k=top_k)


__all__ = [
    "STALE_TIME",
    "STILL_WEAK_REWRITE",
    "STRONG_REWRITE",
    "WEAK_QUERY",
    "WEAK_QUERY_BY_LANGUAGE",
    "ScriptedRewriteLLM",
    "make_outcome",
    "make_request",
    "make_retry_pipeline",
    "run_linear_reference",
    "stale_chunk",
]
