"""Enrichment keeps ids, recomputes hashes, and is idempotent (L4, L6)."""

from __future__ import annotations

import pytest

from packages.ingestion.tests.chunking.fixtures import heading_document, past_paper_document
from uni_rag_core.fakes.llm import FakeLLM
from uni_rag_ingestion.chunking.domain.identity import content_hash
from uni_rag_ingestion.chunking.service import STRATEGIES, Chunker
from uni_rag_ingestion.enrichment.domain.context_blurb import BLURB_MARKER
from uni_rag_ingestion.enrichment.service import Enricher, enrich


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_enrichment_adds_one_blurb_and_keeps_chunk_ids(strategy: str) -> None:
    chunks = Chunker(strategy).chunk(heading_document())
    enriched = Enricher().enrich(chunks)

    assert len(enriched) == len(chunks)
    for original, result in zip(chunks, enriched, strict=True):
        assert result.chunk_id == original.chunk_id
        assert result.doc_id == original.doc_id
        assert result.page == original.page
        assert result.image_ref == original.image_ref
        assert result.text.count(BLURB_MARKER) == 1
        assert result.text.endswith(original.text)
        assert result.content_hash == content_hash(result.text)
        assert result.token_count > original.token_count


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_enrichment_is_idempotent(strategy: str) -> None:
    chunks = Chunker(strategy).chunk(heading_document())
    once = enrich(chunks, FakeLLM())
    twice = enrich(once, FakeLLM())

    assert [c.model_dump_json() for c in once] == [c.model_dump_json() for c in twice]


def test_enrichment_preserves_past_paper_page_and_image() -> None:
    chunks = Chunker("fixed_window").chunk(past_paper_document())
    enriched = Enricher().enrich(chunks)

    assert [c.page for c in enriched] == [1, 1, 1]
    assert [c.image_ref.ref_id for c in enriched if c.image_ref] == [
        "page-1-q1",
        "page-1-q2",
        "page-1-q3",
    ]
