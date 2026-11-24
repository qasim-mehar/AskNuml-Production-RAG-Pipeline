"""Same document in, byte-identical chunks out (L4)."""

from __future__ import annotations

import pytest

from packages.ingestion.tests.chunking.fixtures import (
    heading_document,
    past_paper_document,
    table_document,
    urdu_document,
)
from uni_rag_ingestion.chunking.service import STRATEGIES, Chunker

ALL_FIXTURES = (heading_document, table_document, urdu_document, past_paper_document)


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("build", ALL_FIXTURES)
def test_two_runs_are_byte_identical(strategy: str, build) -> None:
    first = Chunker(strategy).chunk(build())
    second = Chunker(strategy).chunk(build())

    assert [c.model_dump_json() for c in first] == [c.model_dump_json() for c in second]


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_chunk_order_is_deterministic(strategy: str) -> None:
    first = Chunker(strategy).chunk(heading_document())
    second = Chunker(strategy).chunk(heading_document())

    assert [c.chunk_index for c in first] == list(range(len(first)))
    assert [c.chunk_index for c in second] == [c.chunk_index for c in first]
