"""Strategy ``sentence_boundary``: heading- and sentence-aware splitting.

Prefers paragraph and sentence boundaries (Latin and Urdu marks), falling back
to whitespace windows only for sentences that exceed the budget. This is the
single intentional difference from ``fixed_window`` for Lane F's ablation.
"""

from __future__ import annotations

from uni_rag_ingestion.chunking.domain.heading_path import prefix_text
from uni_rag_ingestion.chunking.domain.model import TEXT_KINDS, ChunkDraft, Section
from uni_rag_ingestion.chunking.domain.split_common import finalize
from uni_rag_ingestion.chunking.domain.token_count import (
    body_budget,
    estimate_tokens,
    pack_units,
    sentence_units,
    word_units,
)

STRATEGY_NAME = "sentence_boundary"


def _units_for_block(text: str, max_body: int) -> list[str]:
    units: list[str] = []
    for sentence in sentence_units(text):
        if estimate_tokens(sentence) > max_body:
            units.extend(word_units(sentence))
        else:
            units.append(sentence)
    return units


def split(section: Section) -> tuple[ChunkDraft, ...]:
    """Pack whole sentences where possible, splitting only oversized ones."""
    _, max_body = body_budget(prefix_text(section.heading_path))
    units: list[str] = []
    for block in section.blocks:
        if block.kind in TEXT_KINDS:
            units.extend(_units_for_block(block.text, max_body))
    return finalize(section, pack_units(units, max_body))
