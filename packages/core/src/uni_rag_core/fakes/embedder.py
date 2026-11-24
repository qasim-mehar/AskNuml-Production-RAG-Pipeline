"""Deterministic in-memory Embedder fake."""

import hashlib
from collections.abc import Sequence


class FakeEmbedder:
    """Hash-based deterministic vectors. No model is downloaded or loaded."""

    def __init__(self, dimension: int = 16) -> None:
        if dimension <= 0:
            msg = "dimension must be positive"
            raise ValueError(msg)
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        """Return the configured vector width."""
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one deterministic vector per input text, in order."""
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append(
                [
                    round(digest[index % len(digest)] / 127.5 - 1.0, 6)
                    for index in range(self._dimension)
                ]
            )
        return vectors
