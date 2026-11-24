"""Stable chunk identity and content hashing (L4, L6).

No wall clock, no randomness and no process-dependent hashing: identifiers are
pure SHA-256 functions of explicitly ordered fields.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from uni_rag_core.schemas.document import Document

_FIELD_SEP = "\x1f"
_PATH_SEP = "\x1e"


def content_hash(text: str) -> str:
    """Return the SHA-256 hex digest of UTF-8 encoded text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_chunk_id(
    document: Document,
    heading_path: Sequence[str],
    text: str,
    chunk_index: int,
) -> str:
    """Derive a stable id from provenance, path, rendered text and position."""
    parts = (
        document.doc_id,
        document.source_url,
        _PATH_SEP.join(heading_path),
        text,
        str(chunk_index),
        document.version,
    )
    return hashlib.sha256(_FIELD_SEP.join(parts).encode("utf-8")).hexdigest()[:32]
