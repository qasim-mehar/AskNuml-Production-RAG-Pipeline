"""Scaffold state for LangGraph control flow (L16).

Plain TypedDict only: no LangGraph symbols are imported, and no graph type is
used by the shipped linear pipeline. The retry-loop fields and the single
``needs_clarification`` field were removed with their nodes' L16 verdicts;
generic fields remain for future control flow.
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
    top_score: float
    trace_id: str
