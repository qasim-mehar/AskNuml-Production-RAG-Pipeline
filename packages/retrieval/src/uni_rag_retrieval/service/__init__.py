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
from uni_rag_retrieval.service.retry_rewrite import (
    RetryRewriteConfig,
    RetryRewriteRequest,
    RewriteOutcome,
    retry_rewrite,
)

__all__ = [
    "RetrievalPipeline",
    "RetryRewriteConfig",
    "RetryRewriteRequest",
    "RewriteOutcome",
    "build_abstention",
    "filter_chunks",
    "hybrid_search",
    "maybe_boost",
    "rerank_candidates",
    "retry_rewrite",
    "route_query",
    "synthesize_answer",
]
