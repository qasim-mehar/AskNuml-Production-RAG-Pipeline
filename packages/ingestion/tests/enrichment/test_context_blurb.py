"""Blurbs are generated through the LLM port and are deterministic (L3, L4)."""

from __future__ import annotations

from packages.ingestion.tests.chunking.fixtures import heading_document
from uni_rag_core.fakes.llm import FakeLLM
from uni_rag_core.schemas.chunk import Chunk
from uni_rag_ingestion.chunking.service import Chunker
from uni_rag_ingestion.enrichment.domain.context_blurb import (
    BLURB_MARKER,
    blurb_prompt,
    generate_blurb,
    normalize_blurb,
    strip_blurb,
)
from uni_rag_ingestion.enrichment.service import enrich


def _one_chunk() -> Chunk:
    return Chunker("fixed_window").chunk(heading_document())[0]


class _RecordingLLM:
    """Test double for the LLM port; records the prompt and system message."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        return "A short deterministic blurb."


def test_blurb_is_generated_through_the_llm_port() -> None:
    chunk = _one_chunk()
    llm = _RecordingLLM()

    blurb = generate_blurb(chunk, llm)

    assert blurb == f"{BLURB_MARKER}A short deterministic blurb."
    assert len(llm.calls) == 1
    prompt, system = llm.calls[0]
    assert system is not None and "Never invent facts" in system
    assert prompt == blurb_prompt(chunk)[0]


def test_blurb_prompt_and_normalisation_are_pure() -> None:
    chunk = _one_chunk()

    assert blurb_prompt(chunk) == blurb_prompt(chunk)
    assert normalize_blurb("  one\n two   three  ") == f"{BLURB_MARKER}one two three"
    assert generate_blurb(chunk, FakeLLM()) == generate_blurb(chunk, FakeLLM())
    assert len(generate_blurb(chunk, FakeLLM())) <= len(BLURB_MARKER) + 160


def test_strip_blurb_removes_only_the_enrichment_line() -> None:
    chunk = _one_chunk()
    blurb = f"{BLURB_MARKER}context line"
    enriched = f"{blurb}\n{chunk.text}"

    assert strip_blurb(enriched) == chunk.text
    assert strip_blurb(chunk.text) == chunk.text


def test_source_text_beginning_with_plain_context_is_never_deleted() -> None:
    chunk = _one_chunk()
    source_like = "Context: this line is source content, not an enrichment marker."
    preserved = chunk.model_copy(update={"text": source_like})

    result = enrich([preserved], FakeLLM())[0]
    assert source_like in result.text
    assert result.text.count(BLURB_MARKER) == 1
    assert strip_blurb(source_like) == source_like
    assert strip_blurb(BLURB_MARKER + "no newline") == BLURB_MARKER + "no newline"
    assert strip_blurb(BLURB_MARKER + "blurb\n   ") == BLURB_MARKER + "blurb\n   "
