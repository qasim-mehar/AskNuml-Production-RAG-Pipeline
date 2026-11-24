"""Heading-path construction and rendering (heading-aware chunking).

The path is the stack of enclosing headings. It is stored on the chunk and
prepended verbatim to the chunk text so retrieval sees the structural context.
"""

from __future__ import annotations

from collections.abc import Sequence

from uni_rag_ingestion.chunking.domain.model import Block, BlockKind, Section


def build_sections(blocks: Sequence[Block]) -> tuple[Section, ...]:
    """Group blocks by resolved heading path, in source order.

    A heading at level N closes the current section and replaces every heading
    at level >= N. Empty sections (consecutive headings) are dropped.
    """
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    current: list[Block] = []
    current_path: tuple[str, ...] = ()

    for block in blocks:
        if block.kind is BlockKind.HEADING:
            if current:
                sections.append(Section(current_path, tuple(current)))
                current = []
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            current_path = tuple(title for _, title in stack)
        else:
            current.append(block)

    if current:
        sections.append(Section(current_path, tuple(current)))
    return tuple(sections)


def prefix_text(heading_path: Sequence[str], reason: str | None = None) -> str:
    """Render the deterministic prefix placed above a chunk body."""
    lines: list[str] = []
    if heading_path:
        lines.append(" > ".join(heading_path))
    if reason:
        lines.append(f"Reason: {reason}")
    return "\n".join(lines) + ("\n" if lines else "")


def render_body(heading_path: Sequence[str], body: str, reason: str | None = None) -> str:
    """Prepend the heading path (and optional reason) to a chunk body."""
    return f"{prefix_text(heading_path, reason)}{body}"
