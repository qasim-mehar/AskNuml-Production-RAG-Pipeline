"""Pure retrieval and answer-quality metrics (L1/L4).

Every function returns a deterministic float in ``[0, 1]``. Denominators are
explicit: an empty ground truth yields ``0.0`` rather than an inflated score.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import log2

from uni_rag_core.schemas import Chunk
from uni_rag_eval.domain.judge import FaithfulnessJudge


def mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean, or ``0.0`` for an empty sequence."""
    return sum(values) / len(values) if values else 0.0


def recall_at_k(retrieved_ids: Sequence[str], expected_ids: Sequence[str], k: int) -> float:
    """Fraction of distinct expected chunk ids found in the first ``k`` results."""
    expected = set(expected_ids)
    if k <= 0 or not expected:
        return 0.0
    return len(set(retrieved_ids[:k]) & expected) / len(expected)


def reciprocal_rank(retrieved_ids: Sequence[str], expected_ids: Sequence[str], k: int) -> float:
    """Reciprocal rank of the first relevant result within the first ``k`` results."""
    expected = set(expected_ids)
    if k <= 0 or not expected:
        return 0.0
    for rank, chunk_id in enumerate(retrieved_ids[:k], start=1):
        if chunk_id in expected:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(
    ranked_lists: Sequence[tuple[Sequence[str], Sequence[str]]], k: int
) -> float:
    """Mean reciprocal rank over ``(retrieved, expected)`` pairs."""
    return mean([reciprocal_rank(retrieved, expected, k) for retrieved, expected in ranked_lists])


def ndcg_at_k(retrieved_ids: Sequence[str], expected_ids: Sequence[str], k: int) -> float:
    """Binary-relevance nDCG@k; ideal gain is all expected chunks ranked first."""
    expected = set(expected_ids)
    if k <= 0 or not expected:
        return 0.0
    dcg = sum(
        (1.0 if chunk_id in expected else 0.0) / log2(position + 2)
        for position, chunk_id in enumerate(retrieved_ids[:k])
    )
    ideal_count = min(len(expected), k)
    idcg = sum(1.0 / log2(position + 2) for position in range(ideal_count))
    return dcg / idcg if idcg else 0.0


def faithfulness(claims: Sequence[str], evidence: Sequence[str], judge: FaithfulnessJudge) -> float:
    """Fraction of claims the judge finds entailed by the shared evidence."""
    if not claims:
        return 0.0
    entailed = sum(1 for claim in claims if judge.judge(claim, evidence).entailed)
    return entailed / len(claims)


def citation_resolution(
    citations: Sequence[tuple[str, object]],
    chunks_by_id: Mapping[str, Chunk],
) -> float:
    """Fraction of citations that resolve to a corpus chunk with matching provenance.

    ``citations`` holds ``(chunk_id, last_crawled)`` pairs. A citation resolves
    only when its chunk id exists in the corpus and its ``Citation.last_crawled``
    equals the chunk's ``Chunk.last_crawled`` (ADR 0007). This reads the typed
    field directly; no text footer is parsed (L5/L6). Returns ``0.0`` when there
    are no citations, so an empty denominator never inflates the score (L1).
    """
    if not citations:
        return 0.0
    resolved = sum(
        1
        for chunk_id, crawled in citations
        if chunk_id in chunks_by_id and crawled == chunks_by_id[chunk_id].last_crawled
    )
    return resolved / len(citations)


def abstention_precision(decisions: Sequence[tuple[bool, bool]]) -> float:
    """Of the answers that abstained, the fraction that should have abstained.

    Each pair is ``(predicted_abstain, expected_abstain)``. No abstentions means
    no measurable precision, reported as ``0.0`` (L1).
    """
    true_positives = sum(1 for predicted, expected in decisions if predicted and expected)
    false_positives = sum(1 for predicted, expected in decisions if predicted and not expected)
    total = true_positives + false_positives
    return true_positives / total if total else 0.0
