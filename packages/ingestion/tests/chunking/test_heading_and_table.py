"""Heading path and table-integrity behaviour (fixtures-first, L12)."""

from __future__ import annotations

import pytest

from packages.ingestion.tests.chunking.fixtures import (
    HEADING_EXPECTED_COUNT,
    HEADING_EXPECTED_PATHS,
    TABLE_EXPECTED_CELLS,
    TABLE_EXPECTED_COUNT,
    document,
    filler,
    heading_document,
    table_document,
)
from uni_rag_core.schemas.chunk import Chunk
from uni_rag_core.schemas.enums import DocType
from uni_rag_ingestion.chunking.domain.heading_path import prefix_text
from uni_rag_ingestion.chunking.domain.model import Block, BlockKind, ParsedDocument
from uni_rag_ingestion.chunking.service import STRATEGIES, Chunker


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_heading_paths_are_prepended_and_correct(strategy: str) -> None:
    chunks: tuple[Chunk, ...] = Chunker(strategy).chunk(heading_document())

    assert len(chunks) == HEADING_EXPECTED_COUNT
    assert [chunk.heading_path for chunk in chunks] == list(HEADING_EXPECTED_PATHS)
    for chunk in chunks:
        assert chunk.text.startswith(prefix_text(chunk.heading_path))


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_table_arrives_whole_with_summary(strategy: str) -> None:
    chunks: tuple[Chunk, ...] = Chunker(strategy).chunk(table_document())

    assert len(chunks) == TABLE_EXPECTED_COUNT
    table_chunks = [chunk for chunk in chunks if "Table summary" in chunk.text]
    assert len(table_chunks) == 1
    table_text = table_chunks[0].text
    assert table_text.startswith(
        prefix_text(table_chunks[0].heading_path, "table kept whole; atomic unit")
    )
    assert "Table summary (4 rows x 2 columns): Field | Detail" in table_text
    for cell in TABLE_EXPECTED_CELLS:
        assert cell in table_text
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[2].chunk_index == 2


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_no_cell_is_split_or_leaks_into_another_chunk(strategy: str) -> None:
    chunks: tuple[Chunk, ...] = Chunker(strategy).chunk(table_document())

    assert sum("Dr. Ayesha Khan" in chunk.text for chunk in chunks) == 1
    assert sum("Credits | 4" in chunk.text for chunk in chunks) == 1
    assert all("Reason:" in chunk.text for chunk in chunks if "Table summary" in chunk.text)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_text_before_and_after_a_table_keeps_source_order(strategy: str) -> None:
    parsed = ParsedDocument(
        document(doc_id="doc-mixed", doc_type=DocType.WEB_PAGE),
        (
            Block(kind=BlockKind.HEADING, text="Section", index=0, level=1),
            Block(kind=BlockKind.PARAGRAPH, text=filler(400), index=1),
            Block(
                kind=BlockKind.TABLE,
                text="",
                index=2,
                table_rows=(("A", "B"), ("1", "2")),
            ),
            Block(kind=BlockKind.PARAGRAPH, text=filler(400), index=3),
        ),
    )

    chunks = Chunker(strategy).chunk(parsed)
    assert len(chunks) == 3
    assert "Table summary" not in chunks[0].text
    assert "Table summary" in chunks[1].text
    assert "Table summary" not in chunks[2].text
