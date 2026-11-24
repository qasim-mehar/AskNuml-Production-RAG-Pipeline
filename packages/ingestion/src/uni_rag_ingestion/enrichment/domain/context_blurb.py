"""Deterministic contextual-blurb template backed by the LLM port (L3, L4).

No provider code lives here: the caller injects an ``LLM`` (``FakeLLM`` in
tests). The prompt/template and all normalisation are pure functions of the
chunk, so enrichment is reproducible and idempotent.
"""

from __future__ import annotations

from uni_rag_core.ports.llm import LLM
from uni_rag_core.schemas.chunk import Chunk

# Reserved sentinel: enrichment owns this exact prefix. Source text that merely
# begins with "Context: " is never treated as an already-enriched chunk.
BLURB_MARKER = "[uni-rag-context] "
_BLURB_MAX_CHARS = 160
_SYSTEM = (
    "You write one short, factual context line for a retrieval chunk. "
    "Never invent facts. Reply with a single line only."
)


def blurb_prompt(chunk: Chunk) -> tuple[str, str]:
    """Return (prompt, system) deterministically derived from a chunk."""
    path = " > ".join(chunk.heading_path) if chunk.heading_path else "(none)"
    prompt = f"source_url: {chunk.source_url}\nheading_path: {path}\nchunk_text: {chunk.text[:600]}"
    return prompt, _SYSTEM


def normalize_blurb(raw: str) -> str:
    """Collapse a completion to one stable, marked line."""
    one_line = " ".join(raw.split())[:_BLURB_MAX_CHARS]
    return f"{BLURB_MARKER}{one_line}"


def strip_blurb(text: str) -> str:
    """Remove a leading enrichment blurb line, if present (idempotency).

    Never deletes content: a marker without a following line is left untouched.
    """
    if text.startswith(BLURB_MARKER):
        _, separator, rest = text.partition("\n")
        return rest if separator and rest.strip() else text
    return text


def generate_blurb(chunk: Chunk, llm: LLM) -> str:
    """Generate one contextual blurb for ``chunk`` through the LLM port."""
    prompt, system = blurb_prompt(chunk)
    return normalize_blurb(llm.complete(prompt, system=system))
