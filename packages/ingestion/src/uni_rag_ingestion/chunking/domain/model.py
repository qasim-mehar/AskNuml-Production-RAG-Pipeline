"""Domain-local input and draft records for chunking (L9).

The frozen core :class:`~uni_rag_core.schemas.document.Document` carries
provenance but no structured content. Until Lane B publishes a contract for
parsed structure, the chunker consumes this domain-local ``ParsedDocument``:
an ordered sequence of blocks. The service maps it onto the frozen ``Chunk``
schema without changing core (see the CONTRACT-CHANGE note in the handoff).
"""

from dataclasses import dataclass
from enum import StrEnum

from uni_rag_core.schemas.chunk import ImageRef
from uni_rag_core.schemas.document import Document


class BlockKind(StrEnum):
    """Kinds of parsed content the splitter understands."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    QUESTION = "question"


TEXT_KINDS = (BlockKind.PARAGRAPH, BlockKind.LIST_ITEM)


@dataclass(frozen=True)
class Block:
    """One parsed block. Position order is meaningful; ``index`` is its slot.

    ``table_rows`` is populated only for tables and preserves cells verbatim so
    a table can be emitted whole without ever splitting mid-cell.
    """

    kind: BlockKind
    text: str
    index: int
    level: int = 0
    table_rows: tuple[tuple[str, ...], ...] = ()
    page: int | None = None
    image_ref: ImageRef | None = None


@dataclass(frozen=True)
class ParsedDocument:
    """Core provenance plus ordered parsed blocks (domain-local adapter input)."""

    document: Document
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class Section:
    """Text under one resolved heading path."""

    heading_path: tuple[str, ...]
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class ChunkDraft:
    """Pre-schema chunk; emitted in source order by the service."""

    heading_path: tuple[str, ...]
    body: str
    page: int | None = None
    image_ref: ImageRef | None = None
    reason: str | None = None
    is_table: bool = False
