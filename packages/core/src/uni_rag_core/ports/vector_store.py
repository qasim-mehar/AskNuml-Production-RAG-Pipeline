"""Vector store port (L3)."""

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from uni_rag_core.schemas import Chunk, VectorHit


@runtime_checkable
class VectorStore(Protocol):
    """Stores chunk vectors and returns similarity hits."""

    def upsert(self, items: Sequence[tuple[Chunk, Sequence[float]]]) -> None:
        """Insert or replace chunk/vector pairs."""
        ...

    def search(
        self,
        vector: Sequence[float],
        *,
        top_k: int,
        filters: Mapping[str, str] | None = None,
    ) -> list[VectorHit]:
        """Return at most ``top_k`` hits ordered by descending similarity.

        Every hit's ``payload`` is a domain ``Chunk`` dump that validates
        losslessly as ``Chunk``; operational storage fields do not cross this
        port (ADR 0010).
        """
        ...

    def delete(self, doc_id: str) -> None:
        """Remove every vector belonging to a document."""
        ...
