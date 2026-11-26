"""Run-only composition handed to Lane F's harness by configuration (L3).

This module is deliberately *outside* ``uni_rag_eval``: the shipped eval package
imports only ``uni_rag_core``. It composes Lane E's **public**
``RetrievalPipeline`` from core ports and real-but-offline adapters. E3 removed
the ``retry_rewrite`` node after its zero-gain L16 verdict; the
``retry_rewrite_enabled`` / ``retry_rewrite_iterations`` constructor flags are
retained dormant and no node is live. This module imports no graph node or
rewrite service (L14/L16). Reversal requires the parked live-transport re-run.

ADR 0010: Lane D's boundary strip has not merged yet. This composition applies
the equivalent in-memory strip at the ``VectorStore`` port and labels the
backend with ``strip_source=in-memory``. No live provider or network call is
made: both provider adapters use their deterministic offline transports (L17).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from qdrant_client import QdrantClient

from uni_rag_core import (
    FakeClock,
    FakeReranker,
    Settings,
    VectorHit,
    VectorStore,
)
from uni_rag_core.schemas import Chunk
from uni_rag_eval.domain.golden import (
    chunks_for_strategy,
    chunks_from_registry,
    load_fixture_registry,
)
from uni_rag_eval.domain.variant import INTEGRATED_CHUNKING, Variant
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore
from uni_rag_retrieval.adapters.google_genai_provider import GoogleGenaiEmbedder, GoogleGenaiLLM
from uni_rag_retrieval.domain.fusion import SearchMode as RetrievalSearchMode
from uni_rag_retrieval.service import RetrievalPipeline

FIXED_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
DIMENSION = 16
TOP_K = 5
_THRESHOLD = 0.35
# ADR 0010's nine operational fields. They stay in Qdrant for filter pushdown
# and are removed here before a VectorHit crosses the port (L3).
_STRIP_FIELDS = frozenset(
    {
        "last_crawled_ts",
        "department",
        "course_code",
        "year",
        "term",
        "is_live",
        "indexed_at",
        "deleted_at",
        "superseded_by",
    }
)


class _ChunkSource:
    """Whole-corpus lexical view, satisfying the published ``ChunkSource`` shape."""

    def __init__(self, chunks: Sequence[Chunk]) -> None:
        self._chunks = tuple(chunks)

    def iter_chunks(self) -> Sequence[Chunk]:
        """Return the indexed corpus in stable order."""
        return self._chunks


class InMemoryStrippedStore:
    """VectorStore decorator applying ADR 0010's domain-clean payload strip."""

    def __init__(self, inner: VectorStore) -> None:
        self._inner = inner

    def upsert(self, items: Sequence[tuple[Chunk, Sequence[float]]]) -> None:
        """Delegate storage unchanged; operational fields remain filterable."""
        self._inner.upsert(items)

    def search(
        self,
        vector: Sequence[float],
        *,
        top_k: int,
        filters: Mapping[str, str] | None = None,
    ) -> list[VectorHit]:
        """Return hits whose payload validates losslessly as a domain ``Chunk``."""
        return [
            hit.model_copy(
                update={
                    "payload": {
                        key: value for key, value in hit.payload.items() if key not in _STRIP_FIELDS
                    }
                }
            )
            for hit in self._inner.search(vector, top_k=top_k, filters=filters)
        ]

    def delete(self, doc_id: str) -> None:
        """Delegate soft delete to the indexed store."""
        self._inner.delete(doc_id)


def _registry():
    path = Path(__file__).resolve().parent / "golden" / "fixture-registry.json"
    return load_fixture_registry(json.loads(path.read_text(encoding="utf-8")))


def _settings() -> Settings:
    """Typed, env-free settings pinned for a deterministic run (L8/L4)."""
    return Settings(
        environment="local",
        qdrant_url="http://127.0.0.1:6333",
        postgres_dsn="postgresql://uni-rag:uni-rag@127.0.0.1:5432/uni_rag",
        minio_endpoint="http://127.0.0.1:9000",
        embedding_dimension=DIMENSION,
        default_top_k=TOP_K,
        abstention_threshold=_THRESHOLD,
    )


def build_pipeline(variant: Variant):
    """Return a fresh ``Query -> Answer`` callable for one ablation variant.

    The only variant-dependent behaviour is the injected ablation axes; the
    ``retry_rewrite`` constructor flags stay dormant after E3's removal. The
    same offline corpus, clock and adapters are used for every run (L1/L4).
    """
    registry = _registry()
    if variant.corpus_strategy == INTEGRATED_CHUNKING:
        chunks = chunks_from_registry(registry)
    else:
        chunks = chunks_for_strategy(registry, variant.corpus_strategy)
    clock = FakeClock(FIXED_TIME)
    store = InMemoryStrippedStore(
        QdrantVectorStore(
            QdrantClient(":memory:"),
            dimension=DIMENSION,
            clock=clock,
            host="in-memory",
        )
    )
    embedder = GoogleGenaiEmbedder(dimension=DIMENSION)
    store.upsert([(chunk, embedder.embed([chunk.text])[0]) for chunk in chunks])
    return RetrievalPipeline(
        settings=_settings(),
        embedder=embedder,
        vector_store=store,
        reranker=FakeReranker(),
        llm=GoogleGenaiLLM(),
        clock=clock,
        chunk_source=_ChunkSource(chunks),
        search_mode=RetrievalSearchMode(variant.search_mode.value),
        rerank_enabled=variant.rerank,
        freshness_boost_enabled=variant.freshness_boost,
        # Dormant constructor flags only: the node itself was removed in E3.
        retry_rewrite_enabled=variant.retry_rewrite,
        retry_rewrite_iterations=1,
    ).run


__all__ = ["InMemoryStrippedStore", "build_pipeline"]
