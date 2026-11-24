"""Shared finalisation for both split strategies (prevents strategy drift)."""

from __future__ import annotations

from collections.abc import Sequence

from uni_rag_core.schemas.chunk import ImageRef
from uni_rag_ingestion.chunking.domain.heading_path import prefix_text
from uni_rag_ingestion.chunking.domain.model import ChunkDraft, Section
from uni_rag_ingestion.chunking.domain.token_count import body_budget, estimate_tokens

SHORT_TAIL_REASON = "short section tail kept whole; atomic unit"


def common_page(section: Section) -> int | None:
    """The common page of a text run, or None when blocks disagree (L5, L13)."""
    value: int | None = None
    for block in section.blocks:
        if block.page is not None:
            if value is None:
                value = block.page
            elif value != block.page:
                return None
    return value


def common_image_ref(section: Section) -> ImageRef | None:
    """The common image ref of a text run, or None when blocks disagree."""
    value: ImageRef | None = None
    for block in section.blocks:
        if block.image_ref is not None:
            if value is None:
                value = block.image_ref
            elif value != block.image_ref:
                return None
    return value


def finalize(section: Section, bodies: Sequence[str]) -> tuple[ChunkDraft, ...]:
    """Turn packed body strings into drafts with shared provenance and order."""
    if not section.blocks:
        return ()
    min_body, _ = body_budget(prefix_text(section.heading_path))
    page = common_page(section)
    image_ref = common_image_ref(section)
    drafts: list[ChunkDraft] = []
    for body in bodies:
        reason = SHORT_TAIL_REASON if estimate_tokens(body) < min_body else None
        drafts.append(
            ChunkDraft(
                heading_path=section.heading_path,
                body=body,
                page=page,
                image_ref=image_ref,
                reason=reason,
            )
        )
    return tuple(drafts)
