"""Result reranking port (L3)."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from uni_rag_core.schemas import Chunk, ScoredChunk


@runtime_checkable
class Reranker(Protocol):
    """Reorders candidate chunks by relevance to a query."""

    def rerank(self, query: str, candidates: Sequence[Chunk]) -> list[ScoredChunk]:
        """Return candidates sorted by descending score with 1-based ranks."""
        ...
