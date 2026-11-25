"""Plain retry-rewrite service: grade strength, rewrite via the LLM port, re-search.

This module is framework-free (L15). The graph node in ``graph/nodes.py`` is a
thin wrapper over :func:`retry_rewrite`, so the capped loop is unit-testable
with fakes alone (L4). The router's language classification is never recomputed
here: the rewrite prompt preserves the query's language and the caller keeps
using the original decision (L7).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from uni_rag_core import (
    LLM,
    Embedder,
    Language,
    Reranker,
    RetrievalError,
    ScoredChunk,
    ValidationError,
    VectorStore,
    get_logger,
)
from uni_rag_retrieval.domain.fusion import ChunkSource, SearchMode
from uni_rag_retrieval.domain.prompts import REWRITE_SYSTEM, build_rewrite_prompt
from uni_rag_retrieval.domain.router import FilterSet

_log = get_logger(__name__)


@dataclass(frozen=True)
class RetryRewriteConfig:
    """Named, injected cap for the rewrite loop (L1, L4, L16).

    The cap is supplied at composition time (the application's settings source)
    rather than read from an environment variable here: core owns the single
    settings module (L8, L14) and has no rewrite setting yet.
    """

    max_iterations: int = 1

    def __post_init__(self) -> None:
        """Reject a non-positive cap before any rewrite is attempted."""
        if self.max_iterations < 1:
            msg = "max_iterations must be at least 1"
            raise ValidationError(msg, context={"max_iterations": self.max_iterations})


@dataclass(frozen=True)
class RetryRewriteRequest:
    """Everything the plain service needs; ports arrive as core protocols (L3).

    ``rerank_enabled`` and ``freshness_boost_enabled`` mirror the pipeline's
    ablation axes so a re-search is graded by the same scoring rule as the
    first pass. ``now`` is the pipeline's injected clock value; the service
    never reads a clock itself (L4).
    """

    query_text: str
    scored: Sequence[ScoredChunk]
    llm: LLM
    embedder: Embedder
    vector_store: VectorStore
    reranker: Reranker
    filters: FilterSet
    language: Language
    top_k: int
    threshold: float
    config: RetryRewriteConfig = field(default_factory=RetryRewriteConfig)
    search_mode: SearchMode = SearchMode.HYBRID
    candidate_multiplier: int = 4
    rrf_k: int = 60
    chunk_source: ChunkSource | None = None
    rerank_enabled: bool = True
    freshness_boost_enabled: bool = False
    now: datetime | None = None
    freshness_half_life_days: float = 365.0


@dataclass(frozen=True)
class RewriteOutcome:
    """Result of the capped loop, including its audit trail (L1, L16)."""

    query_text: str
    scored: tuple[ScoredChunk, ...]
    attempts: int
    rewrite_history: tuple[str, ...]
    top_score: float
    strong: bool


def top_score_of(scored: Sequence[ScoredChunk]) -> float:
    """Return the leading (possibly freshness-boosted) score, or 0.0 if empty."""
    return scored[0].score if scored else 0.0


def retry_rewrite(request: RetryRewriteRequest) -> RewriteOutcome:
    """Grade retrieval, then rewrite and re-search until strong or capped out.

    The loop only runs while the leading score is below ``request.threshold``
    and the attempt count is below ``config.max_iterations``. Each rewrite goes
    through the injected ``LLM`` port, and every re-search reuses the same
    deterministic search, rerank and freshness stages as the linear path with
    the same ablation axes (L3, L4, L15). A still-weak outcome is returned
    unchanged for the caller to abstain on (L13); the loop never fabricates a
    stronger score.
    """
    # Imported here to break the import cycle: pipeline composes this service,
    # while the re-search reuses pipeline's named linear stages unchanged.
    from uni_rag_retrieval.service.pipeline import (
        hybrid_search,
        maybe_boost,
        rerank_candidates,
    )

    attempts = 0
    history: list[str] = []
    current_text = request.query_text
    scored = tuple(request.scored)
    top_score = top_score_of(scored)

    while attempts < request.config.max_iterations and top_score < request.threshold:
        rewrite = request.llm.complete(
            build_rewrite_prompt(current_text), system=REWRITE_SYSTEM
        ).strip()
        if not rewrite:
            msg = "rewrite LLM returned an empty completion"
            raise RetrievalError(msg, context={"query_text": current_text})
        history.append(rewrite)
        current_text = rewrite
        attempts += 1

        candidates = hybrid_search(
            current_text,
            embedder=request.embedder,
            vector_store=request.vector_store,
            top_k=request.top_k,
            language=request.language,
            filters=request.filters,
            search_mode=request.search_mode,
            candidate_multiplier=request.candidate_multiplier,
            rrf_k=request.rrf_k,
            chunk_source=request.chunk_source,
        )
        rescored = rerank_candidates(
            current_text,
            candidates,
            reranker=request.reranker,
            enabled=request.rerank_enabled,
            language=request.language,
        )
        scored = tuple(
            maybe_boost(
                rescored,
                enabled=request.freshness_boost_enabled,
                now=request.now,
                half_life_days=request.freshness_half_life_days,
            )
        )
        top_score = top_score_of(scored)
        _log.debug(
            "retry_rewrite.attempt",
            attempt=attempts,
            top_score=top_score,
            strong=top_score >= request.threshold,
        )

    return RewriteOutcome(
        query_text=current_text,
        scored=scored,
        attempts=attempts,
        rewrite_history=tuple(history),
        top_score=top_score,
        strong=top_score >= request.threshold,
    )


__all__ = [
    "RetryRewriteConfig",
    "RetryRewriteRequest",
    "RewriteOutcome",
    "retry_rewrite",
    "top_score_of",
]
