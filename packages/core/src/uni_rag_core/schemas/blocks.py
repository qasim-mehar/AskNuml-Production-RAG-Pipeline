"""Minimal shared vocabulary for structured document blocks (ADR 0007)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from uni_rag_core.schemas.chunk import ImageRef


class BlockKind(StrEnum):
    """Kinds of parsed content shared by parsers, chunkers and golden data."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    QUESTION = "question"


class ContentBlock(BaseModel):
    """One ordered block of parsed content; tables keep their cells verbatim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: BlockKind
    text: str
    index: int
    level: int = 0
    table_rows: tuple[tuple[str, ...], ...] = ()
    page: int | None = None
    image_ref: ImageRef | None = None
