"""Both provider adapters pass the shared contracts offline (L15, L17)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from tests.contracts.port_contracts import assert_embedder_contract, assert_llm_contract
from uni_rag_core import FakeObjectStore, PortError, StorageError
from uni_rag_core.schemas import ImageRef
from uni_rag_retrieval.adapters.google_genai_provider import (
    GoogleGenaiEmbedder,
    GoogleGenaiLLM,
    GoogleGenaiPageImages,
)
from uni_rag_retrieval.adapters.openai_provider import OpenAIEmbedder, OpenAILLM

# Live calls are opt-in only. ADR 0002 leaves the opt-in setting to a Lane 0
# CONTRACT-CHANGE PR, so this test-only flag stays False until that lands.
LIVE_MODE = False

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "uni_rag_retrieval"
_FRAMEWORK_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+(?:google|langchain|langgraph|openai)\b", re.MULTILINE
)
_DYNAMIC_IMPORT = re.compile(r"""import_module\(\s*["'](?:google|langchain|langgraph|openai)\b""")


def test_google_genai_adapters_pass_shared_contracts_offline() -> None:
    assert_llm_contract(GoogleGenaiLLM())
    assert_embedder_contract(GoogleGenaiEmbedder(dimension=16))


def test_openai_adapters_pass_shared_contracts_offline() -> None:
    assert_llm_contract(OpenAILLM())
    assert_embedder_contract(OpenAIEmbedder(dimension=16))


def test_page_images_use_object_store_and_a_frozen_image_ref() -> None:
    store = FakeObjectStore()
    handler = GoogleGenaiPageImages(object_store=store, dimension=16)
    ref = ImageRef(
        ref_id="images/doc-1/p1.png",
        source_url="https://example.edu/papers/2024.pdf",
        page=1,
    )
    data = b"\x89PNG\r\n\x1a\nfixture"

    assert handler.store_page(ref, data) == ref.ref_id
    assert store.get(ref.ref_id) == data
    vector = handler.embed_page(ref)
    assert len(vector) == 16
    assert vector == handler.embed_page(ref)


def test_adapter_transport_failures_are_typed_and_not_swallowed() -> None:
    def broken_transport(prompt: str, system: str | None) -> str:
        raise RuntimeError("transport down")

    with pytest.raises(PortError):
        GoogleGenaiLLM(transport=broken_transport).complete("hello")
    with pytest.raises(PortError):
        OpenAILLM(transport=broken_transport).complete("hello")

    def empty_transport(prompt: str, system: str | None) -> str:
        return ""

    with pytest.raises(PortError):
        OpenAILLM(transport=empty_transport).complete("hello")


def test_adapters_reject_wrong_vector_shapes() -> None:
    def wrong_shape(texts: Any, dimension: int) -> list[list[float]]:
        return [[0.0] for _ in texts]

    with pytest.raises(PortError):
        GoogleGenaiEmbedder(dimension=16, transport=wrong_shape).embed(["a"])
    with pytest.raises(PortError):
        OpenAIEmbedder(dimension=16, transport=wrong_shape).embed(["a"])


def test_adapters_enforce_the_frozen_embedder_value_bounds() -> None:
    def out_of_range(texts: Any, dimension: int) -> list[list[float]]:
        return [[2.0 for _ in range(dimension)] for _ in texts]

    vectors = GoogleGenaiEmbedder(dimension=16, transport=out_of_range).embed(["a"])
    assert vectors == [[1.0] * 16]

    def non_finite(texts: Any, dimension: int) -> list[list[float]]:
        return [[float("nan") for _ in range(dimension)] for _ in texts]

    with pytest.raises(PortError):
        OpenAIEmbedder(dimension=16, transport=non_finite).embed(["a"])


def test_page_image_failures_propagate_or_are_typed() -> None:
    store = FakeObjectStore()
    handler = GoogleGenaiPageImages(object_store=store, dimension=16)
    ref = ImageRef(ref_id="images/missing.png", source_url="https://example.edu/p.pdf", page=1)

    with pytest.raises(StorageError, match="object not found"):
        handler.embed_page(ref)

    def broken(data: bytes, mime_type: str) -> list[float]:
        raise RuntimeError("image transport down")

    store.put(ref.ref_id, b"fixture", content_type=ref.mime_type)
    failing = GoogleGenaiPageImages(object_store=store, dimension=16, transport=broken)
    with pytest.raises(PortError):
        failing.embed_page(ref)


def test_framework_imports_stay_outside_graph_and_adapters() -> None:
    allowed = {"adapters", "graph"}
    for path in _SOURCE_ROOT.rglob("*.py"):
        if set(path.relative_to(_SOURCE_ROOT).parts) & allowed:
            continue
        source = path.read_text(encoding="utf-8")
        assert _FRAMEWORK_IMPORT.search(source) is None, str(path)
        assert _DYNAMIC_IMPORT.search(source) is None, str(path)


@pytest.mark.skipif(not LIVE_MODE, reason="live provider calls are opt-in only (ADR 0002)")
def test_live_provider_calls_are_never_run_in_ci() -> None:
    from uni_rag_retrieval.adapters.google_genai_provider import live_completion_transport

    transport = live_completion_transport(model="gemini-2.0-flash")
    assert transport("hello", None).strip()
