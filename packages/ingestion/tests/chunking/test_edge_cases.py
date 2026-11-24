"""Edge-case L6 provenance and empty/atomic sections (review pass)."""

from __future__ import annotations

import pytest

from packages.ingestion.tests.chunking.fixtures import document, filler
from uni_rag_core.schemas.chunk import ImageRef
from uni_rag_ingestion.chunking.domain.model import Block, BlockKind, ParsedDocument
from uni_rag_ingestion.chunking.service import STRATEGIES, Chunker


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_empty_document_yields_no_chunks(strategy: str) -> None:
    assert Chunker(strategy).chunk(ParsedDocument(document(), ())) == ()


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_table_only_section_yields_one_whole_chunk(strategy: str) -> None:
    parsed = ParsedDocument(
        document(),
        (
            Block(kind=BlockKind.HEADING, text="Table only", index=0, level=1),
            Block(
                kind=BlockKind.TABLE,
                text="",
                index=1,
                table_rows=(("A", "B"), ("1", "2")),
            ),
        ),
    )

    chunks = Chunker(strategy).chunk(parsed)
    assert len(chunks) == 1
    assert "Table summary (2 rows x 2 columns): A | B" in chunks[0].text
    assert chunks[0].heading_path == ["Table only"]


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_disagreeing_pages_abstain_instead_of_guessing(strategy: str) -> None:
    parsed = ParsedDocument(
        document(),
        (
            Block(kind=BlockKind.HEADING, text="Mixed pages", index=0, level=1),
            Block(kind=BlockKind.PARAGRAPH, text=filler(400), index=1, page=1),
            Block(kind=BlockKind.PARAGRAPH, text=filler(400), index=2, page=9),
        ),
    )

    chunks = Chunker(strategy).chunk(parsed)
    assert len(chunks) == 2
    assert all(chunk.page is None for chunk in chunks)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_disagreeing_image_refs_abstain(strategy: str) -> None:
    ref_a = ImageRef(ref_id="a", source_url="https://example.edu.pk/a.pdf")
    ref_b = ImageRef(ref_id="b", source_url="https://example.edu.pk/b.pdf")
    parsed = ParsedDocument(
        document(),
        (
            Block(kind=BlockKind.HEADING, text="Mixed refs", index=0, level=1),
            Block(kind=BlockKind.PARAGRAPH, text=filler(400), index=1, image_ref=ref_a),
            Block(kind=BlockKind.PARAGRAPH, text=filler(400), index=2, image_ref=ref_b),
        ),
    )

    chunks = Chunker(strategy).chunk(parsed)
    assert len(chunks) == 2
    assert all(chunk.image_ref is None for chunk in chunks)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_question_without_page_keeps_its_image_ref(strategy: str) -> None:
    ref = ImageRef(ref_id="scan-1", source_url="https://example.edu.pk/p.pdf")
    parsed = ParsedDocument(
        document(),
        (
            Block(kind=BlockKind.HEADING, text="Scan", index=0, level=1),
            Block(kind=BlockKind.QUESTION, text=filler(400), index=1, image_ref=ref),
        ),
    )

    chunks = Chunker(strategy).chunk(parsed)
    assert len(chunks) == 1
    assert chunks[0].page is None
    assert chunks[0].image_ref == ref
