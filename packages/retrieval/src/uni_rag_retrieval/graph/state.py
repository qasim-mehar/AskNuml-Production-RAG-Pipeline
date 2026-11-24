"""Scaffold state for LangGraph control flow (L16).

Plain TypedDict only: no LangGraph symbols are imported, and no graph type is
used by the shipped linear pipeline. The retry fields thread the capped loop's
counters and rewrite audit trail when a graph is wired later.
"""

from __future__ import annotations

from typing import TypedDict

from uni_rag_core import Answer, Chunk, Query, ScoredChunk
from uni_rag_retrieval.domain.router import RouteDecision


class RetrievalState(TypedDict, total=False):
    """Fields a future graph may thread between nodes."""

    query: Query
    decision: RouteDecision
    candidates: list[Chunk]
    scored: list[ScoredChunk]
    answer: Answer | None
    attempt: int
    max_attempts: int
    top_score: float
    strength_ok: bool
    rewritten_text: str | None
    rewrite_history: list[str]
    needs_clarification: bool
    trace_id: str
