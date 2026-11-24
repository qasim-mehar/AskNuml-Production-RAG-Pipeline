"""Test-only ChunkSource double for the lexical-only ablation axis (L1, L16)."""

from __future__ import annotations

from collections.abc import Sequence

from uni_rag_core.schemas import Chunk


class CorpusChunkSource:
    """Expose a fixed chunk corpus to in-domain lexical scoring."""

    def __init__(self, chunks: Sequence[Chunk]) -> None:
        self._chunks = tuple(chunks)

    def iter_chunks(self) -> Sequence[Chunk]:
        """Return the fixed corpus in fixture order."""
        return self._chunks
