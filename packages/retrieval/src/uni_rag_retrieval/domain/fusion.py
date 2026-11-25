"""Reciprocal-rank fusion, lexical scoring and freshness math (L1, L9).

All functions here are pure: no clock reads, no I/O, no provider calls. The
Clock port's value is injected by the service before freshness is applied.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from uni_rag_core.errors import ValidationError
from uni_rag_core.schemas import Chunk, Language, ScoredChunk, VectorHit
from uni_rag_retrieval.domain.normalize import tokens


class SearchMode(StrEnum):
    """Named ablation axes for search recall (Lane F)."""

    DENSE = "dense"
    LEXICAL = "lexical"
    HYBRID = "hybrid"


@runtime_checkable
class ChunkSource(Protocol):
    """Domain-local source for true lexical recall (no new core port, L3).

    When injected, lexical and hybrid search read the whole indexed corpus
    instead of only the dense candidate pool, so the lexical-only ablation is
    measurable (L1, L16).
    """

    def iter_chunks(self) -> Sequence[Chunk]:
        """Return the chunks available to in-domain lexical scoring."""
        ...


@dataclass(frozen=True)
class LexicalHit:
    """An in-domain lexical result; the chunk itself lives in the dense pool."""

    chunk_id: str
    score: float


def rrf(*rankings: Sequence[str], k: int = 60) -> list[str]:
    """Fuse rankings by reciprocal rank, breaking ties on chunk id."""
    if k <= 0:
        msg = "rrf constant must be positive"
        raise ValidationError(msg, context={"k": k})
    scores: dict[str, float] = {}
    seen: set[str] = set()
    for ranking in rankings:
        seen.update(ranking)
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(seen, key=lambda chunk_id: (-scores.get(chunk_id, 0.0), chunk_id))


def fuse(dense: Sequence[VectorHit], lexical: Sequence[LexicalHit], *, k: int = 60) -> list[str]:
    """Fuse dense and lexical hit lists into one deterministic chunk-id order."""
    return rrf([hit.chunk_id for hit in dense], [hit.chunk_id for hit in lexical], k=k)


def lexical_search(
    query: str,
    chunks: Sequence[Chunk],
    *,
    top_k: int,
    language: Language | None = None,
) -> list[LexicalHit]:
    """Score candidate chunks by normalized query-token overlap."""
    if top_k <= 0:
        return []
    query_tokens = set(tokens(query, language=language))
    hits: list[LexicalHit] = []
    for chunk in chunks:
        chunk_tokens = set(tokens(chunk.text, language=language))
        chunk_tokens.update(tokens(" ".join(chunk.heading_path), language=language))
        score = len(query_tokens & chunk_tokens) / len(query_tokens) if query_tokens else 0.0
        hits.append(LexicalHit(chunk_id=chunk.chunk_id, score=round(score, 6)))
    hits.sort(key=lambda hit: (-hit.score, hit.chunk_id))
    return hits[:top_k]


def score_candidates(
    query: str,
    chunks: Sequence[Chunk],
    *,
    language: Language | None = None,
) -> list[ScoredChunk]:
    """Rank chunks by lexical overlap when the Reranker port is ablated off."""
    hits = lexical_search(query, chunks, top_k=len(chunks), language=language)
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    return [
        ScoredChunk(chunk=by_id[hit.chunk_id], score=hit.score, rank=rank)
        for rank, hit in enumerate(hits, start=1)
        if hit.chunk_id in by_id
    ]


def freshness_multiplier(last_crawled: datetime, now: datetime, *, half_life_days: float) -> float:
    """Return a decay factor in (0, 1] for evidence of a given age."""
    if last_crawled.tzinfo is None or now.tzinfo is None:
        msg = "freshness requires timezone-aware datetimes"
        raise ValidationError(msg)
    if half_life_days <= 0:
        msg = "half_life_days must be positive"
        raise ValidationError(msg, context={"half_life_days": half_life_days})
    age_days = float(max(0.0, (now - last_crawled).total_seconds() / 86400.0))
    return float(2.0 ** (-age_days / half_life_days))


def apply_freshness_boost(
    scored: Sequence[ScoredChunk],
    *,
    now: datetime,
    half_life_days: float,
) -> list[ScoredChunk]:
    """Multiply scores by freshness and re-rank deterministically."""
    boosted = [
        item.model_copy(
            update={
                "score": round(
                    item.score
                    * freshness_multiplier(
                        item.chunk.last_crawled, now, half_life_days=half_life_days
                    ),
                    6,
                )
            }
        )
        for item in scored
    ]
    boosted.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
    return [item.model_copy(update={"rank": rank}) for rank, item in enumerate(boosted, start=1)]


__all__ = [
    "ChunkSource",
    "LexicalHit",
    "SearchMode",
    "apply_freshness_boost",
    "freshness_multiplier",
    "fuse",
    "lexical_search",
    "rrf",
    "score_candidates",
]
