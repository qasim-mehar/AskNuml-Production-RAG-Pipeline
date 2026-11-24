"""Pure normalization of parsed tables into whole row/column records (L9)."""

from __future__ import annotations

from collections.abc import Sequence

from uni_rag_core.errors import ParseError
from uni_rag_ingestion.parsers.domain.models import ParsedTable, TableRecord


def normalize_tables(tables: Sequence[ParsedTable]) -> tuple[TableRecord, ...]:
    """Normalize tables without dropping columns, rows or cell text.

    Raises:
        ParseError: if a table is empty or has a row whose width differs from
            its header; widths must never be silently padded or truncated.
    """
    records: list[TableRecord] = []
    for table in tables:
        header = tuple(cell.strip() for cell in table.header)
        rows = tuple(
            tuple(cell.strip() for cell in row)
            for row in table.rows
            if any(cell.strip() for cell in row)
        )
        if not header or any(len(row) != len(header) for row in rows):
            raise ParseError(
                "table is empty or ragged",
                context={"page": table.page, "header_width": len(header)},
            )
        records.append(TableRecord(page=table.page, header=header, rows=rows))
    return tuple(records)
