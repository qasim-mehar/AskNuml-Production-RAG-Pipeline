"""Urdu and Roman Urdu survive chunking without loss or reordering (L7)."""

from __future__ import annotations

import pytest

from packages.ingestion.tests.chunking.fixtures import (
    URDU_EXPECTED_WORDS,
    document,
    filler,
    urdu_document,
)
from uni_rag_ingestion.chunking.domain.heading_path import prefix_text
from uni_rag_ingestion.chunking.domain.model import Block, BlockKind, ParsedDocument
from uni_rag_ingestion.chunking.service import STRATEGIES, Chunker


def _body(chunk) -> str:  # type: ignore[no-untyped-def]
    prefix = prefix_text(chunk.heading_path)
    assert chunk.text.startswith(prefix)
    lines = [
        line for line in chunk.text[len(prefix) :].split("\n") if not line.startswith("Reason:")
    ]
    return "\n".join(lines)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_urdu_words_are_preserved_in_order(strategy: str) -> None:
    chunks = Chunker(strategy).chunk(urdu_document())

    words = [word for chunk in chunks for word in _body(chunk).split()]
    assert tuple(words) == URDU_EXPECTED_WORDS
    assert "".join(words) == "".join(URDU_EXPECTED_WORDS)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_roman_urdu_words_are_preserved_in_order(strategy: str) -> None:
    source = "Roman Urdu " + filler(900)
    parsed = ParsedDocument(
        document(doc_id="doc-roman", language="roman_urdu"),
        (
            Block(kind=BlockKind.HEADING, text="Roman Urdu", index=0, level=1),
            Block(kind=BlockKind.PARAGRAPH, text=source, index=1),
        ),
    )

    chunks = Chunker(strategy).chunk(parsed)
    words = [word for chunk in chunks for word in _body(chunk).split()]
    assert words == source.split()
