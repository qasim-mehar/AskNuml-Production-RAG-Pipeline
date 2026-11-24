"""Deterministic in-memory Reranker fake."""

import re
from collections.abc import Sequence

from uni_rag_core.schemas import Chunk, ScoredChunk

_TOKEN = re.compile(r"\w+", flags=re.UNICODE)


class FakeReranker:
    """Ranks by query-token overlap, with stable tie-breaking by chunk id."""

    def rerank(self, query: str, candidates: Sequence[Chunk]) -> list[ScoredChunk]:
        """Score candidates by token overlap against the query."""
        query_tokens = set(_TOKEN.findall(query.lower()))
        scored = [self._score(chunk, query_tokens) for chunk in candidates]
        order = sorted(range(len(candidates)), key=lambda i: (-scored[i], candidates[i].chunk_id))
        return [
            ScoredChunk(chunk=candidates[i], score=scored[i], rank=rank)
            for rank, i in enumerate(order, 1)
        ]

    @staticmethod
    def _score(chunk: Chunk, query_tokens: set[str]) -> float:
        if not query_tokens:
            return 0.0
        text_tokens = set(_TOKEN.findall(chunk.text.lower()))
        return len(text_tokens & query_tokens) / len(query_tokens)
