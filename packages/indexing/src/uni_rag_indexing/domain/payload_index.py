"""Deterministic in-memory payload/vector index used in fake mode (L4/L9).

It shares every predicate with the Qdrant adapter, so filter-correctness and
idempotency numbers measured here describe the same semantics as live mode.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from math import sqrt
from typing import Any

from uni_rag_core import Chunk, Clock, FakeClock, VectorHit, get_logger
from uni_rag_indexing.domain.filters import (
    build_payload,
    matches_payload,
    point_id,
    soft_delete_payload,
    translate_filters,
)

_logger = get_logger("uni_rag_indexing.domain.payload_index")


class PayloadVectorIndex:
    """Brute-force cosine index with live payload filtering and soft deletes."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock: Clock = clock or FakeClock()
        self._items: dict[str, dict[str, Any]] = {}
        self._vectors: dict[str, tuple[float, ...]] = {}

    def upsert(self, items: Sequence[tuple[Chunk, Sequence[float]]]) -> None:
        """Insert or replace chunk/vector pairs; identical data is a no-op."""
        for chunk, vector in items:
            pid = point_id(chunk)
            existing = self._items.get(pid)
            if existing is not None and self._same(existing, chunk):
                continue
            stamp = self._clock.now()
            # Retire every live version of this chunk id before writing the new
            # one; the vector is kept, only its lifecycle flags change.
            self._soften_chunk(chunk.chunk_id, superseded_by=pid, deleted_at=stamp)
            self._items[pid] = build_payload(chunk, indexed_at=stamp)
            self._vectors[pid] = tuple(float(value) for value in vector)
            _logger.debug("fake_upsert", chunk_id=chunk.chunk_id, point_id=pid)

    def search(
        self,
        vector: Sequence[float],
        *,
        top_k: int,
        filters: Mapping[str, str] | None = None,
    ) -> list[VectorHit]:
        """Return at most ``top_k`` live hits ordered by cosine similarity."""
        if top_k <= 0:
            return []
        spec = translate_filters(filters).with_live()
        query = tuple(float(value) for value in vector)
        hits: list[VectorHit] = []
        for pid, payload in self._items.items():
            if not matches_payload(payload, spec):
                continue
            score = self._cosine(query, self._vectors[pid])
            hits.append(
                VectorHit(
                    chunk_id=str(payload["chunk_id"]),
                    score=round(score, 6),
                    payload=dict(payload),
                )
            )
        hits.sort(key=lambda hit: (-hit.score, hit.chunk_id))
        return hits[:top_k]

    def delete(self, doc_id: str) -> None:
        """Soft-delete every live chunk of a document (vectors are retained)."""
        stamp = self._clock.now()
        for pid, payload in list(self._items.items()):
            if payload["doc_id"] == doc_id and payload["is_live"]:
                self._items[pid] = soft_delete_payload(
                    payload, deleted_at=stamp, superseded_by=None
                )

    def mark_stale(self, chunk_id: str, *, superseded_by: str, deleted_at: datetime) -> None:
        """Soft-delete live points for ``chunk_id`` without dropping vectors."""
        self._soften_chunk(chunk_id, superseded_by=superseded_by, deleted_at=deleted_at)

    def is_present(self, chunk_id: str) -> bool:
        """Return True when a live point exists for ``chunk_id``."""
        return any(
            payload.get("chunk_id") == chunk_id and payload.get("is_live")
            for payload in self._items.values()
        )

    def payloads(self, *, include_stale: bool = False) -> list[dict[str, Any]]:
        """Return stored payloads; stale ones are included for history tooling."""
        return [
            dict(payload)
            for payload in self._items.values()
            if include_stale or payload.get("is_live")
        ]

    def _soften_chunk(self, chunk_id: str, *, superseded_by: str, deleted_at: datetime) -> None:
        for pid, payload in list(self._items.items()):
            if payload.get("chunk_id") == chunk_id and payload.get("is_live"):
                self._items[pid] = soft_delete_payload(
                    payload, deleted_at=deleted_at, superseded_by=superseded_by
                )

    @staticmethod
    def _same(payload: Mapping[str, Any], chunk: Chunk) -> bool:
        return (
            payload.get("content_hash") == chunk.content_hash
            and payload.get("version") == chunk.version
            and payload.get("is_live") is True
        )

    @staticmethod
    def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        denom = sqrt(sum(value * value for value in left)) * sqrt(
            sum(value * value for value in right)
        )
        if denom == 0.0:
            return 0.0
        return sum(a * b for a, b in zip(left, right, strict=False)) / denom
