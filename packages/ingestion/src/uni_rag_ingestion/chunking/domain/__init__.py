"""Pure, deterministic domain logic for heading-aware chunking.

No I/O, no clock, no randomness: every function here is a function of its
arguments alone (L4, L9).
"""

from uni_rag_ingestion.chunking.domain.identity import content_hash, make_chunk_id
from uni_rag_ingestion.chunking.domain.model import (
    Block,
    BlockKind,
    ChunkDraft,
    ParsedDocument,
    Section,
)
from uni_rag_ingestion.chunking.domain.token_count import (
    TARGET_MAX,
    TARGET_MIN,
    body_budget,
    estimate_tokens,
)

__all__ = [
    "TARGET_MAX",
    "TARGET_MIN",
    "Block",
    "BlockKind",
    "ChunkDraft",
    "ParsedDocument",
    "Section",
    "body_budget",
    "content_hash",
    "estimate_tokens",
    "make_chunk_id",
]
