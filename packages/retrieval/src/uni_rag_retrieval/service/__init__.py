"""Plain orchestration functions and the linear pipeline (L9)."""

from uni_rag_retrieval.service.pipeline import (
    RetrievalPipeline,
    build_abstention,
    filter_chunks,
    hybrid_search,
    maybe_boost,
    rerank_candidates,
    route_query,
    synthesize_answer,
)

__all__ = [
    "RetrievalPipeline",
    "build_abstention",
    "filter_chunks",
    "hybrid_search",
    "maybe_boost",
    "rerank_candidates",
    "route_query",
    "synthesize_answer",
]
