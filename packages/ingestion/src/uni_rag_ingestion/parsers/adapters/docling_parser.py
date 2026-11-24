"""Docling adapter for digital PDFs and HTML (ADR-0003, L3/L4).

Docling is imported lazily. When the library is unavailable this adapter
logs the fact and reads the checked-in fixtures deterministically; that
fallback is not Docling and is reported as such in the Lane B handoff.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast, runtime_checkable

from uni_rag_core.errors import ParseError
from uni_rag_core.logging import get_logger
from uni_rag_ingestion.parsers.adapters._fixture_extract import (
    parse_html_fixture,
    parse_pdf_fixture,
)
from uni_rag_ingestion.parsers.domain.models import ParsedDocument, ParsedPage, ParsedTable

_logger = get_logger("uni_rag.parsers.docling")


@runtime_checkable
class DoclingPage(Protocol):
    """The page surface this adapter needs from Docling."""

    def export_to_text(self) -> str: ...


@runtime_checkable
class DoclingTable(Protocol):
    """The table surface this adapter needs from Docling."""

    def export_to_dict(self) -> dict[str, object]: ...


@runtime_checkable
class DoclingDocument(Protocol):
    """The document surface this adapter needs from Docling."""

    @property
    def pages(self) -> Sequence[DoclingPage]: ...

    @property
    def tables(self) -> Sequence[DoclingTable]: ...


@runtime_checkable
class DoclingResult(Protocol):
    """A Docling conversion result."""

    @property
    def document(self) -> DoclingDocument: ...


@runtime_checkable
class DoclingEngine(Protocol):
    """Minimal converter protocol; satisfied by Docling's DocumentConverter."""

    def convert(self, source: str) -> DoclingResult: ...


def _load_engine() -> DoclingEngine | None:
    """Return a Docling converter when the optional dependency is installed."""
    try:
        from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]
    except ImportError:
        return None
    return cast(DoclingEngine, DocumentConverter())


def _string_tuple(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    return tuple(str(cell).strip() for cell in value)


def _string_rows(value: object) -> tuple[tuple[str, ...], ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    rows: list[tuple[str, ...]] = []
    for row in value:
        cells = _string_tuple(row)
        if cells is None:
            return None
        rows.append(cells)
    return tuple(rows)


def _with_source(exc: ParseError, source_path: Path) -> ParseError:
    if "source_path" in exc.context:
        return exc
    return ParseError(exc.message, context={**exc.context, "source_path": str(source_path)})


def _map_tables(document: DoclingDocument, source_path: Path) -> dict[int, list[ParsedTable]]:
    """Map Docling table dictionaries to page-numbered tables."""
    by_page: dict[int, list[ParsedTable]] = {}
    for item in document.tables:
        data = item.export_to_dict()
        header = _string_tuple(data.get("header"))
        rows = _string_rows(data.get("rows"))
        page_value = data.get("page", 1)
        if header is None or rows is None or not isinstance(page_value, int):
            raise ParseError(
                "unsupported Docling table shape",
                context={"keys": sorted(data), "source_path": str(source_path)},
            )
        by_page.setdefault(page_value, []).append(
            ParsedTable(page=page_value, header=header, rows=rows)
        )
    return by_page


def _parse_fixture(source_path: Path) -> ParsedDocument:
    suffix = source_path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return parse_html_fixture(source_path)
    if suffix == ".pdf":
        return parse_pdf_fixture(source_path)
    raise ParseError(
        "unsupported source kind for the Docling adapter",
        context={"source_path": str(source_path), "suffix": suffix},
    )


class DoclingParser:
    """Parse digital PDFs and HTML into pages with text, tables and page numbers.

    Args:
        engine: optional injected converter. Tests inject a fake that honours
            :class:`DoclingEngine`; production uses Docling when installed.
        prefer_docling: when false, skip the lazy library import and use the
            deterministic fixture reader. Tests pin this for reproducibility.
    """

    def __init__(
        self,
        *,
        engine: DoclingEngine | None = None,
        prefer_docling: bool = True,
    ) -> None:
        self._engine = engine
        self._prefer_docling = prefer_docling

    def parse(self, source_path: Path) -> ParsedDocument:
        """Parse ``source_path`` into ordered pages.

        Raises:
            ParseError: if conversion fails, produces no pages, or the source
                kind is unsupported; the source path is always in the context.
        """
        try:
            engine = (
                self._engine
                if self._engine is not None
                else (_load_engine() if self._prefer_docling else None)
            )
        except (OSError, ValueError, TypeError) as exc:
            raise ParseError(
                "could not initialise the Docling engine",
                context={"source_path": str(source_path)},
            ) from exc
        if engine is None:
            _logger.warning(
                "docling.unavailable",
                source_path=str(source_path),
                fallback="fixture-extract",
            )
            return _parse_fixture(source_path)

        try:
            document = engine.convert(str(source_path)).document
            tables = _map_tables(document, source_path)
            pages = tuple(
                ParsedPage(
                    page=number,
                    text=page.export_to_text(),
                    tables=tuple(tables.get(number, ())),
                )
                for number, page in enumerate(document.pages, start=1)
            )
        except ParseError as exc:
            raise _with_source(exc, source_path) from exc
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise ParseError(
                "Docling conversion failed",
                context={"source_path": str(source_path)},
            ) from exc
        if not pages:
            raise ParseError("Docling produced no pages", context={"source_path": str(source_path)})
        return ParsedDocument(pages=pages)
