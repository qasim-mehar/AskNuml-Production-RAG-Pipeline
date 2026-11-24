"""Strategy ``fixed_window``: heading-aware fixed token windows (L1, L7).

Splits on whitespace boundaries only; sentence boundaries are deliberately
ignored. Language-neutral: no English-specific sentence or token rule.
"""

from __future__ import annotations

from uni_rag_ingestion.chunking.domain.heading_path import prefix_text
from uni_rag_ingestion.chunking.domain.model import TEXT_KINDS, ChunkDraft, Section
from uni_rag_ingestion.chunking.domain.split_common import finalize
from uni_rag_ingestion.chunking.domain.token_count import (
    body_budget,
    pack_units,
    word_units,
)

STRATEGY_NAME = "fixed_window"


def split(section: Section) -> tuple[ChunkDraft, ...]:
    """Pack a section's text into fixed windows of up to the budgeted size."""
    _, max_body = body_budget(prefix_text(section.heading_path))
    units: list[str] = []
    for block in section.blocks:
        if block.kind in TEXT_KINDS:
            units.extend(word_units(block.text))
    return finalize(section, pack_units(units, max_body))
