"""RRF fusion and freshness math specs (L1, L9). Fixture orders, not live metrics."""

from __future__ import annotations

from datetime import datetime

import pytest

from packages.retrieval.tests.fixtures.corpus import FIXED_TIME, OLD_TIME, build_corpus
from uni_rag_core import Chunk, ScoredChunk, ValidationError
from uni_rag_retrieval.domain.fusion import (
    apply_freshness_boost,
    freshness_multiplier,
    fuse,
    lexical_search,
    rrf,
)


def _scored(chunk: Chunk, score: float, rank: int) -> ScoredChunk:
    return ScoredChunk(chunk=chunk, score=score, rank=rank)


def test_rrf_fusion_beats_dense_only_on_fixture_order() -> None:
    dense = ["chunk-distractor", "chunk-target", "chunk-other"]
    lexical = ["chunk-target", "chunk-other", "chunk-distractor"]
    fused = rrf(dense, lexical)
    assert dense[0] == "chunk-distractor"
    assert fused[0] == "chunk-target"
    assert fused == ["chunk-target", "chunk-distractor", "chunk-other"]


def test_fusion_is_deterministic_and_ties_break_on_chunk_id() -> None:
    assert rrf(["b", "a"], ["a", "b"]) == ["a", "b"]
    assert rrf(["b", "a"], ["a", "b"]) == rrf(["b", "a"], ["a", "b"])


def test_freshness_boost_reorders_equal_relevance_pairs() -> None:
    corpus = build_corpus()
    newer = next(chunk for chunk in corpus if chunk.chunk_id == "chunk-fresh-new")
    older = next(chunk for chunk in corpus if chunk.chunk_id == "chunk-fresh-old")
    scored = [_scored(older, 0.7, 1), _scored(newer, 0.7, 2)]

    boosted = apply_freshness_boost(scored, now=FIXED_TIME, half_life_days=365.0)

    assert [item.chunk.chunk_id for item in boosted] == ["chunk-fresh-new", "chunk-fresh-old"]
    assert [item.rank for item in boosted] == [1, 2]
    assert boosted[0].score > boosted[1].score
    assert boosted == apply_freshness_boost(scored, now=FIXED_TIME, half_life_days=365.0)


def test_freshness_multiplier_is_bounded_and_increasing() -> None:
    fresh = freshness_multiplier(FIXED_TIME, FIXED_TIME, half_life_days=365.0)
    stale = freshness_multiplier(OLD_TIME, FIXED_TIME, half_life_days=365.0)
    assert fresh == 1.0
    assert 0.0 < stale < fresh


def test_freshness_rejects_naive_datetimes() -> None:
    naive = datetime(2026, 1, 1, 0, 0, 0)
    with pytest.raises(ValidationError):
        freshness_multiplier(naive, FIXED_TIME, half_life_days=365.0)


def test_lexical_search_scores_and_ties_are_stable() -> None:
    corpus = [chunk for chunk in build_corpus() if chunk.chunk_id.startswith("chunk-fresh")]
    hits = lexical_search("Freshness policy reference note", corpus, top_k=2)
    assert [hit.chunk_id for hit in hits] == ["chunk-fresh-new", "chunk-fresh-old"]
    assert hits[0].score == hits[1].score


def test_fuse_accepts_vector_hits_from_the_frozen_schema() -> None:
    from uni_rag_core.schemas import VectorHit

    hits = [VectorHit(chunk_id="a", score=0.9), VectorHit(chunk_id="b", score=0.8)]
    assert fuse(hits, [], k=60) == ["a", "b"]
