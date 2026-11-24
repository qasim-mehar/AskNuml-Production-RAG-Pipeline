"""Pure value objects and the parser port for the parsing domain (L9)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from uni_rag_core import ImageRef, PastPaperQuestion


@dataclass(frozen=True, slots=True)
class ParsedTable:
    """One table on a source page, in reading order."""

    page: int
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """Text and tables for one source page; ``image`` holds raw image bytes when present."""

    page: int
    text: str
    tables: tuple[ParsedTable, ...] = ()
    image: bytes | None = None


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Ordered pages produced by a source parser."""

    pages: tuple[ParsedPage, ...]


@dataclass(frozen=True, slots=True)
class PaperMetadata:
    """Cover-page metadata extracted by pure domain logic."""

    course_code: str
    year: int
    term: str
    exam_type: str
    department: str

    def as_dict(self) -> dict[str, str | int]:
        """Return field-name-to-value pairs used for accuracy scoring."""
        return {
            "course_code": self.course_code,
            "year": self.year,
            "term": self.term,
            "exam_type": self.exam_type,
            "department": self.department,
        }


@dataclass(frozen=True, slots=True)
class QuestionSpan:
    """A segmented question and any option lines that belong to it."""

    question_number: int
    text: str
    page: int
    options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TableRecord:
    """A normalized table kept whole, with its header and row structure."""

    page: int
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    """Everything the parsing lane emits for one source document."""

    questions: tuple[PastPaperQuestion, ...]
    metadata: PaperMetadata
    tables: tuple[TableRecord, ...]
    image_refs: dict[int, ImageRef]


@runtime_checkable
class DocumentParser(Protocol):
    """Source-agnostic parse port, defined domain-local (L3)."""

    def parse(self, source_path: Path) -> ParsedDocument:
        """Read ``source_path`` and return its ordered pages."""
        ...
