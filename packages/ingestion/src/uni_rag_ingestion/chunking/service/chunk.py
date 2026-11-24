"""Chunking orchestration: strategy selection and Chunk assembly (L6, L9).

Selection is a constructor argument, never a settings key (L8). This module
contains no split math and no I/O; it delegates to domain functions.
"""

from __future__ import annotations

from collections.abc import Callable

from uni_rag_core.errors import ValidationError
from uni_rag_core.schemas.chunk import Chunk
from uni_rag_ingestion.chunking.domain.heading_path import build_sections, render_body
from uni_rag_ingestion.chunking.domain.identity import content_hash, make_chunk_id
from uni_rag_ingestion.chunking.domain.model import ChunkDraft, ParsedDocument, Section
from uni_rag_ingestion.chunking.domain.strategy_fixed_window import (
    STRATEGY_NAME as FIXED_WINDOW,
)
from uni_rag_ingestion.chunking.domain.strategy_fixed_window import split as fixed_window
from uni_rag_ingestion.chunking.domain.strategy_sentence import (
    STRATEGY_NAME as SENTENCE_BOUNDARY,
)
from uni_rag_ingestion.chunking.domain.strategy_sentence import split as sentence_boundary
from uni_rag_ingestion.chunking.domain.table_guard import segment
from uni_rag_ingestion.chunking.domain.token_count import estimate_tokens

STRATEGIES = (FIXED_WINDOW, SENTENCE_BOUNDARY)
_SPLITTERS: dict[str, Callable[[Section], tuple[ChunkDraft, ...]]] = {
    FIXED_WINDOW: fixed_window,
    SENTENCE_BOUNDARY: sentence_boundary,
}


class Chunker:
    """Select a chunking strategy at construction and emit complete Chunks.

    The same ``ParsedDocument`` always yields byte-identical output (L4).
    """

    def __init__(self, strategy: str = FIXED_WINDOW) -> None:
        if strategy not in STRATEGIES:
            msg = f"unknown chunking strategy: {strategy}"
            raise ValidationError(msg, context={"strategy": strategy, "known": list(STRATEGIES)})
        self._strategy = strategy

    @property
    def strategy(self) -> str:
        """The selected strategy name (stable id for Lane F's ablation)."""
        return self._strategy

    def chunk(self, parsed: ParsedDocument) -> tuple[Chunk, ...]:
        """Split a parsed document into deterministic, L6-complete chunks."""
        drafts: list[ChunkDraft] = []
        for section in build_sections(parsed.blocks):
            for part in segment(section):
                if isinstance(part, ChunkDraft):
                    drafts.append(part)
                else:
                    drafts.extend(_SPLITTERS[self._strategy](part))

        document = parsed.document
        chunks: list[Chunk] = []
        for index, draft in enumerate(drafts):
            text = render_body(draft.heading_path, draft.body, draft.reason)
            chunks.append(
                Chunk(
                    chunk_id=make_chunk_id(document, draft.heading_path, text, index),
                    doc_id=document.doc_id,
                    source_url=document.source_url,
                    heading_path=list(draft.heading_path),
                    content_hash=content_hash(text),
                    last_crawled=document.last_crawled,
                    doc_type=document.doc_type,
                    version=document.version,
                    language=document.language,
                    text=text,
                    chunk_index=index,
                    token_count=estimate_tokens(text),
                    page=draft.page,
                    image_ref=draft.image_ref,
                )
            )
        return tuple(chunks)
