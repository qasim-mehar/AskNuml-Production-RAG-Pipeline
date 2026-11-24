"""L6 completeness, size band, identity and constructor validation."""

from __future__ import annotations

import pytest

from packages.ingestion.tests.chunking.fixtures import (
    heading_document,
    past_paper_document,
    table_document,
    urdu_document,
)
from uni_rag_core.errors import ValidationError
from uni_rag_core.schemas.chunk import Chunk
from uni_rag_ingestion.chunking.domain.identity import content_hash, make_chunk_id
from uni_rag_ingestion.chunking.service import STRATEGIES, Chunker

ALL_FIXTURES = (heading_document, table_document, urdu_document, past_paper_document)
MANDATORY = (
    "chunk_id",
    "doc_id",
    "source_url",
    "heading_path",
    "content_hash",
    "last_crawled",
    "doc_type",
    "version",
)


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("build", ALL_FIXTURES)
def test_every_chunk_carries_l6_fields(strategy: str, build) -> None:
    parsed = build()
    chunks: tuple[Chunk, ...] = Chunker(strategy).chunk(parsed)

    assert chunks, "fixture must yield chunks"
    for index, chunk in enumerate(chunks):
        dumped = chunk.model_dump()
        for field in MANDATORY:
            assert dumped[field] is not None, f"{field} missing on chunk {index}"
        assert chunk.chunk_index == index
        assert chunk.doc_id == parsed.document.doc_id
        assert chunk.source_url == parsed.document.source_url
        assert chunk.last_crawled == parsed.document.last_crawled
        assert chunk.doc_type == parsed.document.doc_type
        assert chunk.version == parsed.document.version
        assert chunk.language == parsed.document.language
        assert chunk.content_hash == content_hash(chunk.text)
        assert chunk.token_count is not None


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("build", (heading_document, table_document, urdu_document))
def test_ordinary_chunks_stay_in_the_300_to_500_band(strategy: str, build) -> None:
    chunks: tuple[Chunk, ...] = Chunker(strategy).chunk(build())

    ordinary = [chunk for chunk in chunks if "Reason:" not in chunk.text]
    assert ordinary, "fixture must contain ordinary chunks"
    for chunk in ordinary:
        assert 300 <= chunk.token_count <= 500, (strategy, chunk.chunk_index, chunk.token_count)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_chunk_id_is_a_stable_function_of_content_and_path(strategy: str) -> None:
    parsed = heading_document()
    first = Chunker(strategy).chunk(parsed)
    second = Chunker(strategy).chunk(parsed)

    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]
    for chunk in first:
        assert chunk.chunk_id == make_chunk_id(
            parsed.document, tuple(chunk.heading_path), chunk.text, chunk.chunk_index
        )


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_past_paper_chunks_keep_page_and_image_ref(strategy: str) -> None:
    chunks: tuple[Chunk, ...] = Chunker(strategy).chunk(past_paper_document())

    assert len(chunks) == 3
    for chunk, (marker, ref_id) in zip(
        chunks,
        (("Q1", "page-1-q1"), ("Q2", "page-1-q2"), ("Q3", "page-1-q3")),
        strict=True,
    ):
        assert chunk.page == 1
        assert chunk.image_ref is not None
        assert chunk.image_ref.ref_id == ref_id
        assert chunk.text.count("Q") >= 1
        assert marker in chunk.text
        assert "Reason: past-paper question kept whole; atomic unit" in chunk.text


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Chunker("not-a-strategy")
