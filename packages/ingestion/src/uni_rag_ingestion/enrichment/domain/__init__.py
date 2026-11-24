"""Pure, deterministic enrichment domain logic (L3, L4, L9)."""

from uni_rag_ingestion.enrichment.domain.context_blurb import (
    BLURB_MARKER,
    blurb_prompt,
    generate_blurb,
    normalize_blurb,
    strip_blurb,
)

__all__ = [
    "BLURB_MARKER",
    "blurb_prompt",
    "generate_blurb",
    "normalize_blurb",
    "strip_blurb",
]
