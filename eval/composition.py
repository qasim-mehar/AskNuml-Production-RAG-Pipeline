"""Run-only composition handed to Lane F's harness by configuration (L3).

This module is deliberately *outside* ``uni_rag_eval``: the shipped eval package
imports only ``uni_rag_core``. It composes Lane E's **public**
``RetrievalPipeline`` from core ports and real-but-offline adapters. E3 removed
the ``retry_rewrite`` node after its zero-gain L16 verdict; the
``retry_rewrite_enabled`` / ``retry_rewrite_iterations`` constructor flags are
retained dormant and no node is live. This module imports no graph node or
rewrite service (L14/L16). Reversal requires the parked live-transport re-run.

F5 adds run-only wrappers for the three registry-only control-flow nodes
(``clarify``, ``multihop``, ``checkpoint_followup``). They ask the injected LLM
port for the structured value each node would need; the offline transport echoes
its prompt, so no value is ever accepted and the single-pass answer is returned
unchanged. No framework node and no production pipeline behaviour is added; a
live transport would be needed before any measured verdict is production
evidence (L1/L16).

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
    LLM,
    Answer,
    Citation,
    FakeClock,
    FakeReranker,
    Query,
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
from uni_rag_eval.domain.variant import INTEGRATED_CHUNKING, NodeVariant, Variant
from uni_rag_eval.runner.harness import RetrievalCallable
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


# Offline transports echo their prompt. A node may only change the answer when
# a transport returns an explicit, well-formed marker line; the echo prefix is
# never accepted as a value. This keeps F5's node-on rows honest (L1/L16).
_ECHO_MARK = "google-genai[offline]"


def _node_marker(completion: str, marker: str) -> str | None:
    """Parse one explicit marker line, rejecting prompt echoes (L1)."""
    if _ECHO_MARK in completion:
        return None
    for line in completion.splitlines():
        if line.startswith(marker):
            return line[len(marker) :].strip() or None
    return None


def _merged_citations(*groups: Sequence[Citation], top_k: int) -> list[Citation]:
    """Merge citation groups by chunk id in stable order, capped at ``top_k``."""
    merged: list[Citation] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item.chunk_id not in seen:
                merged.append(item)
                seen.add(item.chunk_id)
    return merged[:top_k]


class MeasuredNode:
    """Run-only wrapper that attempts a control-flow node through the LLM port.

    The wrapper calls the single-pass callable, then asks the injected LLM for
    the structured value the node would need. Offline transports echo their
    prompt, so no value is accepted and the answer is unchanged; Lane F records
    the reversal condition on every report (L1/L16). No graph node or shipped
    pipeline behaviour is introduced here.
    """

    def __init__(
        self, inner: RetrievalCallable, *, llm: LLM, node: NodeVariant, top_k: int
    ) -> None:
        self._inner = inner
        self._llm = llm
        self._node = node
        self._top_k = top_k

    def __call__(self, query: Query) -> Answer:
        """Return the node-on answer for one query."""
        answer = self._inner(query)
        if self._node is NodeVariant.CLARIFY:
            return self._clarify(query, answer)
        if self._node is NodeVariant.MULTIHOP:
            return self._multihop(query, answer)
        if self._node is NodeVariant.CHECKPOINT_FOLLOWUP:
            return self._checkpoint(query, answer)
        return answer

    def _clarify(self, query: Query, answer: Answer) -> Answer:
        """Ask for the missing required filter; re-query only if a value is supplied."""
        if not answer.abstained:
            return answer
        completion = self._llm.complete(
            "If a required filter is missing, reply with one line "
            "CLARIFY_DOC_ID=<doc id>, otherwise reply NONE. "
            f"Question: {query.text}"
        )
        doc_id = _node_marker(completion, "CLARIFY_DOC_ID=")
        if doc_id is None:
            return answer
        clarified = query.model_copy(update={"filters": {**query.filters, "doc_id": doc_id}})
        return self._inner(clarified)

    def _multihop(self, query: Query, answer: Answer) -> Answer:
        """Ask for a second-document query; merge its citations only if supplied."""
        if answer.abstained or not answer.citations:
            return answer
        completion = self._llm.complete(
            "If a second document is needed, reply with one line "
            "MULTIHOP_QUERY=<query>, otherwise reply NONE. "
            f"Question: {query.text}"
        )
        followup = _node_marker(completion, "MULTIHOP_QUERY=")
        if followup is None:
            return answer
        second = self._inner(
            query.model_copy(update={"query_id": f"{query.query_id}-hop2", "text": followup})
        )
        if second.abstained:
            return answer
        citations = _merged_citations(answer.citations, second.citations, top_k=self._top_k)
        return answer.model_copy(update={"citations": citations})

    def _checkpoint(self, query: Query, answer: Answer) -> Answer:
        """Carry prior-turn citations into a follow-up only if ids are supplied."""
        completion = self._llm.complete(
            "Reply with one line FOLLOWUP_CITATIONS=<comma-separated chunk ids> "
            "carried into the checkpointed follow-up. "
            f"Prior turn: {answer.text}"
        )
        carried = _node_marker(completion, "FOLLOWUP_CITATIONS=")
        if carried is None:
            return answer
        followup = self._inner(query.model_copy(update={"query_id": f"{query.query_id}-followup"}))
        carried_ids = [part.strip() for part in carried.split(",") if part.strip()]
        by_id = {item.chunk_id: item for item in [*followup.citations, *answer.citations]}
        ordered = [by_id[item_id] for item_id in carried_ids if item_id in by_id]
        seen = {item.chunk_id for item in ordered}
        for item in [*answer.citations, *followup.citations]:
            if item.chunk_id not in seen:
                ordered.append(item)
                seen.add(item.chunk_id)
        return answer.model_copy(update={"citations": ordered[: self._top_k]})


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
    pipeline = RetrievalPipeline(
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
    if variant.node_variant is NodeVariant.SINGLE_PASS:
        return pipeline
    return MeasuredNode(pipeline, llm=GoogleGenaiLLM(), node=variant.node_variant, top_k=TOP_K)


__all__ = ["InMemoryStrippedStore", "build_pipeline"]
