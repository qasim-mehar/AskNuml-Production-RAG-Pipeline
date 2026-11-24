"""Enrichment orchestration: chunks in, enriched chunks out (L4, L9).

Prepends one LLM-generated contextual blurb per chunk, keeps ``chunk_id``
stable, and recomputes ``content_hash``/``token_count`` for the enriched text.
Running enrichment on already-enriched chunks is byte-identical.
"""

from __future__ import annotations

from collections.abc import Iterable

from uni_rag_core.fakes.llm import FakeLLM
from uni_rag_core.ports.llm import LLM
from uni_rag_core.schemas.chunk import Chunk
from uni_rag_ingestion.chunking.domain.identity import content_hash
from uni_rag_ingestion.chunking.domain.token_count import estimate_tokens
from uni_rag_ingestion.enrichment.domain.context_blurb import generate_blurb, strip_blurb


class Enricher:
    """Prepend a deterministic contextual blurb to each chunk (FakeLLM default)."""

    def __init__(self, llm: LLM | None = None) -> None:
        self._llm: LLM = llm if llm is not None else FakeLLM()

    def enrich(self, chunks: Iterable[Chunk]) -> tuple[Chunk, ...]:
        """Return enriched copies; input chunks are never mutated (L4)."""
        return enrich(chunks, self._llm)


def enrich(chunks: Iterable[Chunk], llm: LLM | None = None) -> tuple[Chunk, ...]:
    """Enrich every chunk. ``llm`` defaults to the deterministic core fake."""
    model: LLM = llm if llm is not None else FakeLLM()
    enriched: list[Chunk] = []
    for chunk in chunks:
        base = strip_blurb(chunk.text)
        base_chunk = chunk.model_copy(update={"text": base})
        text = f"{generate_blurb(base_chunk, model)}\n{base}"
        enriched.append(
            chunk.model_copy(
                update={
                    "text": text,
                    "content_hash": content_hash(text),
                    "token_count": estimate_tokens(text),
                }
            )
        )
    return tuple(enriched)
