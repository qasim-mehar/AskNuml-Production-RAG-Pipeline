"""Deterministic in-memory VectorStore fake."""

from collections.abc import Mapping, Sequence
from math import sqrt

from uni_rag_core.schemas import Chunk, VectorHit


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
        """Return at most ``top_k`` hits sorted by descending cosine similarity."""
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
                    chunk_id=chunk_id, score=round(score, 6), payload=chunk.model_dump(mode="json")
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
