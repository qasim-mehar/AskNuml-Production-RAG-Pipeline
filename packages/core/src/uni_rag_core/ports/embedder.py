"""Text embedding port (L3)."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Turns text into fixed-width dense vectors."""

    @property
    def dimension(self) -> int:
        """Dimensionality of every vector produced by this embedder."""
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts, preserving input order."""
        ...
