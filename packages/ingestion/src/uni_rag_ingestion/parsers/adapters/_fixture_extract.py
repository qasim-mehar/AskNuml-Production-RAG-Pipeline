"""Dependency-free extraction of checked-in fixtures (L4).

This module is used when a real parser library is unavailable. It is not an
OCR or a general-purpose PDF engine: it reads the synthetic, text-bearing
fixtures shipped with this lane and preserves their text and table cells.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from uni_rag_core.errors import ParseError
from uni_rag_ingestion.parsers.domain.models import ParsedDocument, ParsedPage, ParsedTable

_BLOCK_TAGS = frozenset({"title", "h1", "h2", "h3", "p", "li"})
_CELL_TAGS = frozenset({"th", "td"})
_OBJECT_RE = re.compile(rb"(\d+)\s+0\s+obj(.*?)endobj", re.DOTALL)
_PAGE_TYPE_RE = re.compile(rb"/Type\s*/Page\b(?!s)")
_CONTENTS_RE = re.compile(rb"/Contents\s+(\d+)\s+0\s+R")
_STRING_RE = re.compile(rb"\(((?:\\.|[^\\()])*)\)", re.DOTALL)


class _HTMLCollector(HTMLParser):
    """Collect block text in reading order plus whole HTML tables."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.tables: list[ParsedTable] = []
        self._buffer: list[str] = []
        self._in_cell = False
        self._cell_parts: list[str] = []
        self._row: list[str] = []
        self._header: list[str] | None = None
        self._rows: list[tuple[str, ...]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS:
            self._buffer = []
        if tag == "table":
            self._header = None
            self._rows = []
        elif tag == "tr":
            self._row = []
        elif tag in _CELL_TAGS:
            self._in_cell = True
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_cell:
            self._cell_parts.append(text)
        else:
            self._buffer.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            line = " ".join(self._buffer).strip()
            if line:
                self.lines.append(line)
            self._buffer = []
        elif tag in _CELL_TAGS:
            self._row.append(" ".join(self._cell_parts).strip())
            self._in_cell = False
        elif tag == "tr":
            cells = tuple(self._row)
            if any(cells):
                if self._header is None:
                    self._header = list(cells)
                else:
                    self._rows.append(cells)
            self._row = []
        elif tag == "table":
            header = tuple(self._header or ())
            if header:
                self.tables.append(ParsedTable(page=1, header=header, rows=tuple(self._rows)))
            self._header = None
            self._rows = []


def parse_html_fixture(source_path: Path) -> ParsedDocument:
    """Extract text and tables from a checked-in HTML fixture as one page."""
    collector = _HTMLCollector()
    collector.feed(source_path.read_text(encoding="utf-8"))
    collector.close()
    page = ParsedPage(
        page=1,
        text="\n".join(collector.lines),
        tables=tuple(collector.tables),
    )
    return ParsedDocument(pages=(page,))


def _decode_pdf_string(raw: bytes) -> str:
    decoded = raw.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")
    return decoded.decode("utf-8")


def parse_pdf_fixture(source_path: Path) -> ParsedDocument:
    """Extract one line per PDF text string, in page order, from a fixture PDF."""
    raw = source_path.read_bytes()
    if not raw.startswith(b"%PDF-"):
        raise ParseError("source is not a PDF", context={"source_path": str(source_path)})
    objects: dict[int, bytes] = {
        int(match.group(1)): match.group(2) for match in _OBJECT_RE.finditer(raw)
    }
    pages: list[ParsedPage] = []
    for body in objects.values():
        if _PAGE_TYPE_RE.search(body) is None:
            continue
        contents = _CONTENTS_RE.search(body)
        if contents is None:
            raise ParseError(
                "PDF page has no content stream", context={"source_path": str(source_path)}
            )
        stream = objects.get(int(contents.group(1)))
        if stream is None:
            raise ParseError(
                "PDF content object is missing", context={"source_path": str(source_path)}
            )
        text = "\n".join(_decode_pdf_string(literal) for literal in _STRING_RE.findall(stream))
        pages.append(ParsedPage(page=len(pages) + 1, text=text))
    if not pages:
        raise ParseError("PDF contains no pages", context={"source_path": str(source_path)})
    return ParsedDocument(pages=tuple(pages))
