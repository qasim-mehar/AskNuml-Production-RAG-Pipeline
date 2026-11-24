"""Measured query latency over the fixture corpus (L1).

The harness prints p50/p95 rather than asserting a guessed threshold: a number
without a stated environment is theatre. Fake mode always runs; live mode runs
only when the compose Qdrant service answers.
"""

from __future__ import annotations

import socket
import time
from typing import Any

import pytest
from qdrant_client import QdrantClient

from tests.factories import FIXED_TIME
from uni_rag_core import Chunk, Embedder, FakeClock, VectorStore, load_settings
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore
from uni_rag_indexing.domain.filters import matches_payload, translate_filters
from uni_rag_indexing.domain.payload_index import PayloadVectorIndex


def _percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def _measure(store: VectorStore, embedder: Embedder, *, filters: dict[str, str]) -> list[float]:
    vector = embedder.embed(["measurement query"])[0]
    timings: list[float] = []
    for _ in range(30):
        start = time.perf_counter()
        store.search(vector, top_k=10, filters=filters)
        timings.append((time.perf_counter() - start) * 1000.0)
    return timings


def _report(
    request: pytest.FixtureRequest, environment: str, filters: dict[str, str], samples: list[float]
) -> None:
    reporter: Any = request.config.pluginmanager.getplugin("terminalreporter")
    line = (
        f"LATENCY [{environment}] filters={filters} n={len(samples)} "
        f"p50={_percentile(samples, 0.50):.3f}ms p95={_percentile(samples, 0.95):.3f}ms"
    )
    if reporter is not None:
        reporter.write_line(line)
    else:  # pragma: no cover - fallback for non-standard runners
        import logging

        logging.getLogger(__name__).info(line)


def _reachable(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("localhost", port)) == 0


@pytest.mark.integration
def test_query_latency_and_filter_correctness_in_fake_mode(
    request: pytest.FixtureRequest,
    corpus: list[Chunk],
    embedder: Embedder,
) -> None:
    index = PayloadVectorIndex(clock=FakeClock(FIXED_TIME))
    index.upsert([(chunk, embedder.embed([chunk.text])[0]) for chunk in corpus])
    filters = {"doc_type": "web_page"}
    samples = _measure(index, embedder, filters=filters)
    expected = {
        payload["chunk_id"]
        for payload in index.payloads()
        if matches_payload(payload, translate_filters(filters))
    }
    actual = {
        hit.chunk_id for hit in index.search(embedder.embed(["q"])[0], top_k=10, filters=filters)
    }
    assert actual == expected and len(actual) == 1
    _report(request, "fake:payload-index", filters, samples)


@pytest.mark.integration
def test_query_latency_and_filter_correctness_in_qdrant_local_mode(
    request: pytest.FixtureRequest,
    corpus: list[Chunk],
    embedder: Embedder,
) -> None:
    """Real Qdrant client, in-process local storage; no Docker required."""
    store = QdrantVectorStore(
        QdrantClient(":memory:"),
        dimension=embedder.dimension,
        clock=FakeClock(FIXED_TIME),
    )
    store.upsert([(chunk, embedder.embed([chunk.text])[0]) for chunk in corpus])
    filters = {"doc_type": "web_page"}
    samples = _measure(store, embedder, filters=filters)
    hits = store.search(embedder.embed(["q"])[0], top_k=10, filters=filters)
    assert len(hits) == 1 and all(hit.payload["doc_type"] == "web_page" for hit in hits)
    _report(request, "qdrant-client:local", filters, samples)


@pytest.mark.integration
def test_query_latency_in_compose_live_mode(
    request: pytest.FixtureRequest,
    corpus: list[Chunk],
    embedder: Embedder,
) -> None:
    if not _reachable(6333):
        pytest.skip("qdrant compose service unreachable on :6333")
    settings = load_settings()
    store = QdrantVectorStore.from_settings(settings, clock=FakeClock(FIXED_TIME))
    store.upsert([(chunk, embedder.embed([chunk.text])[0]) for chunk in corpus])
    filters = {"doc_type": "web_page"}
    samples = _measure(store, embedder, filters=filters)
    _report(request, "compose:qdrant-live", filters, samples)
