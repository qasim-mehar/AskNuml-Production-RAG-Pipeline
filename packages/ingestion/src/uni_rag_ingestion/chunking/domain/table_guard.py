"""Table and question guard: atomic units are never split (L6, L9).

Each table becomes one whole chunk with a deterministic one-line summary.
Past-paper questions are likewise atomic so a question number and its image
reference stay together on a single chunk.
"""

from __future__ import annotations

from uni_rag_ingestion.chunking.domain.model import Block, BlockKind, ChunkDraft, Section

TABLE_REASON = "table kept whole; atomic unit"
QUESTION_REASON = "past-paper question kept whole; atomic unit"


def table_summary(rows: tuple[tuple[str, ...], ...]) -> str:
    """Build a short, deterministic summary line from a table's cells."""
    if not rows:
        return "Table summary (0 rows x 0 columns)"
    width = max(len(row) for row in rows)
    header = " | ".join(rows[0]) if rows[0] else "(empty header)"
    return f"Table summary ({len(rows)} rows x {width} columns): {header}"


def render_table(rows: tuple[tuple[str, ...], ...]) -> str:
    """Render the whole table as pipe-delimited rows, cells verbatim."""
    return "\n".join(" | ".join(row) for row in rows)


def segment(section: Section) -> tuple[Section | ChunkDraft, ...]:
    """Split a section into ordered text runs and atomic drafts.

    A table or question breaks the text run, so text before and after it is
    split independently and source order is preserved exactly.
    """
    segments: list[Section | ChunkDraft] = []
    run: list[Block] = []

    def flush() -> None:
        if run:
            segments.append(Section(section.heading_path, tuple(run)))
            run.clear()

    for block in section.blocks:
        if block.kind is BlockKind.TABLE:
            flush()
            rows = block.table_rows
            body = f"{table_summary(rows)}\n{render_table(rows)}"
            segments.append(
                ChunkDraft(
                    heading_path=section.heading_path,
                    body=body,
                    page=block.page,
                    image_ref=block.image_ref,
                    reason=TABLE_REASON,
                    is_table=True,
                )
            )
        elif block.kind is BlockKind.QUESTION:
            flush()
            segments.append(
                ChunkDraft(
                    heading_path=section.heading_path,
                    body=block.text,
                    page=block.page,
                    image_ref=block.image_ref,
                    reason=QUESTION_REASON,
                )
            )
        else:
            run.append(block)
    flush()
    return tuple(segments)
