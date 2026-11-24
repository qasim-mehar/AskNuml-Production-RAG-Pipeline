# mypy: disable-error-code=import-untyped
"""Scaffold state for future LangGraph control flow (L16).

Plain TypedDict only: no LangGraph symbols are imported, and no graph type is
used by the shipped linear pipeline.
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
    needs_clarification: bool
    trace_id: str
