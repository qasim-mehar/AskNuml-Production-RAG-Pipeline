"""Deterministic in-memory VectorStore fake."""

from collections.abc import Mapping, Sequence
from math import sqrt
from typing import Any

from uni_rag_core.schemas import Chunk, VectorHit

# The exact field list from eval/reports/INTEGRATION-BLOCKER.md (512be58).
# Lane D stores these for filter pushdown; ADR 0010 forbids returning them
# through the VectorStore port. Kept here so the contract suite exercises the
# real collision instead of a simplified approximation.
OPERATIONAL_FIELDS: tuple[str, ...] = (
    "last_crawled_ts",
    "department",
    "course_code",
    "year",
    "term",
    "is_live",
    "indexed_at",
    "deleted_at",
    "superseded_by",
)

# A fixed stamp keeps the fake deterministic (L4): no wall clock leaks in.
_INDEXED_AT = "2026-01-01T00:00:00+00:00"


def stored_payload(chunk: Chunk) -> dict[str, Any]:
    """Return the raw stored payload, operational fields included.

    Mirrors Lane D's ``build_payload``: every operational value is derived from
    the chunk or a fixed constant, so repeated calls are identical (L4).
    """
    payload: dict[str, Any] = chunk.model_dump(mode="json")
    notes = chunk.metadata or {}
    payload.update(
        {
            "last_crawled_ts": chunk.last_crawled.timestamp(),
            "department": notes.get("department", "General"),
            "course_code": notes.get("course_code", "GEN-000"),
            "year": notes.get("year", "0"),
            "term": notes.get("term", "N/A"),
            "is_live": True,
            "indexed_at": _INDEXED_AT,
            "deleted_at": None,
            "superseded_by": None,
        }
    )
    return payload


def strip_operational_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the domain-clean payload a VectorHit is allowed to carry (ADR 0010)."""
    return {key: value for key, value in payload.items() if key not in OPERATIONAL_FIELDS}


class FakeVectorStore:
    """Brute-force cosine similarity over an in-memory dictionary."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[Chunk, tuple[float, ...]]] = {}

    def upsert(self, items: Sequence[tuple[Chunk, Sequence[float]]]) -> None:
        """Insert or replace chunk/vector pairs keyed by chunk id."""
        for chunk, vector in items:
            self._items[chunk.chunk_id] = (chunk, tuple(float(value) for value in vector))

    def search(
        self,
        vector: Sequence[float],
        *,
        top_k: int,
        filters: Mapping[str, str] | None = None,
    ) -> list[VectorHit]:
        """Return at most ``top_k`` hits sorted by descending cosine similarity.

        Hits carry only the domain-clean payload; operational fields survive in
        the stored payload but are stripped at the port boundary (ADR 0010).
        """
        if top_k <= 0:
            return []
        query = tuple(float(value) for value in vector)
        query_norm = self._norm(query)
        hits: list[VectorHit] = []
        for chunk_id, (chunk, stored) in self._items.items():
            if not self._matches(chunk, filters):
                continue
            denom = query_norm * self._norm(stored)
            score = self._dot(query, stored) / denom if denom else 0.0
            hits.append(
                VectorHit(
                    chunk_id=chunk_id,
                    score=round(score, 6),
                    payload=strip_operational_fields(stored_payload(chunk)),
                )
            )
        hits.sort(key=lambda hit: (-hit.score, hit.chunk_id))
        return hits[:top_k]

    def delete(self, doc_id: str) -> None:
        """Remove every chunk belonging to ``doc_id``."""
        for chunk_id in [key for key, (chunk, _) in self._items.items() if chunk.doc_id == doc_id]:
            del self._items[chunk_id]

    @staticmethod
    def _matches(chunk: Chunk, filters: Mapping[str, str] | None) -> bool:
        if not filters:
            return True
        values = {
            "doc_id": chunk.doc_id,
            "source_url": chunk.source_url,
            "doc_type": str(chunk.doc_type.value),
            "language": chunk.language.value,
            "version": chunk.version,
        }
        return all(values.get(key) == value for key, value in filters.items())

    @staticmethod
    def _norm(vector: tuple[float, ...]) -> float:
        return sqrt(sum(value * value for value in vector))

    @staticmethod
    def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=False))
