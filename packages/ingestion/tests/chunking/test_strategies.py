"""Strategy comparison: same mandatory fields, different split policy (L1)."""

from __future__ import annotations

import pytest

from packages.ingestion.tests.chunking.fixtures import SENTENCE_EXPECTED_COUNT, sentence_document
from uni_rag_ingestion.chunking.domain.heading_path import prefix_text
from uni_rag_ingestion.chunking.service import STRATEGIES, Chunker

FIXED, SENTENCE = "fixed_window", "sentence_boundary"


def test_strategy_names_are_stable_ablation_ids() -> None:
    assert STRATEGIES == (FIXED, SENTENCE)
    assert Chunker(FIXED).strategy == FIXED
    assert Chunker(SENTENCE).strategy == SENTENCE


def test_sentence_boundary_ends_chunks_on_sentences_fixed_window_does_not() -> None:
    fixed = Chunker(FIXED).chunk(sentence_document())
    sentence = Chunker(SENTENCE).chunk(sentence_document())

    assert len(fixed) == SENTENCE_EXPECTED_COUNT
    assert len(sentence) == SENTENCE_EXPECTED_COUNT

    def body(chunk) -> str:  # type: ignore[no-untyped-def]
        return chunk.text[len(prefix_text(chunk.heading_path)) :].strip()

    assert all(body(chunk).endswith(".") for chunk in sentence)
    assert not body(fixed[0]).endswith(".")
    assert body(fixed[0]) != body(sentence[0])


@pytest.mark.parametrize("build", (sentence_document,))
def test_both_strategies_emit_the_same_mandatory_field_values(build) -> None:
    fixed = Chunker(FIXED).chunk(build())
    sentence = Chunker(SENTENCE).chunk(build())

    fields = ("doc_id", "source_url", "last_crawled", "doc_type", "version", "language")
    for field in fields:
        assert [getattr(c, field) for c in fixed] == [getattr(c, field) for c in sentence]
    assert [c.heading_path for c in fixed] == [c.heading_path for c in sentence]
