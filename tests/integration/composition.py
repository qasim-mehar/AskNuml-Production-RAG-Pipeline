"""Service-level composition of real adapters behind the frozen core ports.

Only this module wires adapters together. Provider and infrastructure objects
are built from typed settings (L8); no ``os.environ`` read and no key is ever
logged (L10). The core fakes stay the default through :class:`AdapterSelection`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import httpx
from qdrant_client import QdrantClient

from tests.integration.selection import AdapterSelection
from uni_rag_core import (
    LLM,
    Answer,
    Clock,
    Embedder,
    FakeClock,
    FakeEmbedder,
    FakeFetcher,
    FakeLLM,
    FakeObjectStore,
    FakeReranker,
    FakeVectorStore,
    Fetcher,
    ObjectStore,
    Query,
    Reranker,
    Settings,
    SystemClock,
    VectorStore,
)
from uni_rag_core.schemas import Chunk
from uni_rag_indexing.adapters.minio_object_store import MinioObjectStore
from uni_rag_indexing.adapters.postgres_metadata_store import PostgresMetadataStore
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore
from uni_rag_ingestion.crawler.adapters.http_fetcher import HttpFetcher
from uni_rag_ingestion.parsers.adapters.docling_parser import DoclingParser
from uni_rag_retrieval.adapters.google_genai_provider import (
    GoogleGenaiEmbedder,
    GoogleGenaiLLM,
    live_completion_transport,
    live_embedding_transport,
)
from uni_rag_retrieval.domain.fusion import ChunkSource, SearchMode
from uni_rag_retrieval.service.pipeline import RetrievalPipeline

_COMPLETION_MODEL = "gemini-2.0-flash"
_EMBEDDING_MODEL = "text-embedding-004"


class _ChunkSource:
    """Domain-local corpus view for hybrid lexical recall (L3)."""

    def __init__(self, chunks: Sequence[Chunk]) -> None:
        self._chunks = tuple(chunks)

    def iter_chunks(self) -> Sequence[Chunk]:
        """Return the indexed corpus in stable order."""
        return self._chunks


@dataclass(frozen=True)
class IntegrationContext:
    """Every port used by one integration run, plus the composed pipeline."""

    selection: AdapterSelection
    settings: Settings
    clock: Clock
    fetcher: Fetcher
    object_store: ObjectStore
    vector_store: VectorStore
    embedder: Embedder
    reranker: Reranker
    llm: LLM
    pipeline: RetrievalPipeline
    chunk_source: ChunkSource | None

    @property
    def backend(self) -> str:
        """Return the labelled backend for reports and logs (L1)."""
        return self.selection.backend_label()

    def ask(self, query: Query) -> Answer:
        """Run the composed pipeline for one query."""
        return self.pipeline.run(query)


def build_fetcher(
    selection: AdapterSelection,
    settings: Settings,
    *,
    conditional_headers_for: Callable[[str], Mapping[str, str]] | None = None,
    client: httpx.Client | None = None,
) -> Fetcher:
    """Build Lane A's real HTTP fetcher or the core fake."""
    if selection.fetcher == "http":
        # ADR 0006: Lane A's adapter is still v1 (one-argument fetch). It satisfies
        # the runtime Protocol for the calls this pass makes; the v2 keyword is
        # deliberately not passed to it. The cast records that migration state.
        return cast(
            Fetcher,
            HttpFetcher(
                client if client is not None else httpx.Client(timeout=10),
                user_agent=settings.crawler.user_agent,
                conditional_headers_for=conditional_headers_for,
            ),
        )
    return FakeFetcher()


def build_parser(selection: AdapterSelection) -> DoclingParser:
    """Build Lane B's parser; the fixture reader is the sanctioned fallback."""
    return DoclingParser(prefer_docling=selection.parser == "docling")


def build_object_store(selection: AdapterSelection, settings: Settings) -> ObjectStore:
    """Build Lane D's MinIO adapter or the core fake."""
    if selection.object_store == "minio":
        return MinioObjectStore.from_settings(settings)
    return FakeObjectStore()


def build_vector_store(
    selection: AdapterSelection, settings: Settings, *, clock: Clock
) -> VectorStore:
    """Build Lane D's Qdrant adapter (local or compose) or the core fake."""
    if selection.vector_store == "qdrant":
        return QdrantVectorStore.from_settings(settings, clock=clock)
    if selection.vector_store == "qdrant_local":
        return QdrantVectorStore(
            QdrantClient(":memory:"),
            dimension=settings.embedding_dimension,
            clock=clock,
            host="in-memory",
        )
    return FakeVectorStore()


def build_metadata_store(
    selection: AdapterSelection, settings: Settings, *, clock: Clock
) -> PostgresMetadataStore | None:
    """Build Lane D's Postgres adapter when selected; compose-only."""
    if selection.metadata == "postgres":
        return PostgresMetadataStore.from_settings(settings, clock=clock)
    return None


def build_providers(
    selection: AdapterSelection, settings: Settings
) -> tuple[Embedder, Reranker, LLM]:
    """Build Lane E's provider adapters in offline mode unless live is opted in."""
    if selection.embedder != "google_genai":
        embedder: Embedder = FakeEmbedder(dimension=settings.embedding_dimension)
    elif selection.live_providers and settings.providers.google_api_key is not None:
        embedder = GoogleGenaiEmbedder(
            dimension=settings.embedding_dimension,
            transport=live_embedding_transport(
                model=_EMBEDDING_MODEL,
                api_key=settings.providers.google_api_key.get_secret_value(),
            ),
        )
    else:
        embedder = GoogleGenaiEmbedder(dimension=settings.embedding_dimension)

    # Lane E ships no real Reranker adapter; lexical scoring stays fake/offline.
    reranker: Reranker = FakeReranker()

    if selection.llm != "google_genai":
        llm: LLM = FakeLLM()
    elif selection.live_providers and settings.providers.google_api_key is not None:
        llm = GoogleGenaiLLM(
            transport=live_completion_transport(
                model=_COMPLETION_MODEL,
                api_key=settings.providers.google_api_key.get_secret_value(),
            )
        )
    else:
        llm = GoogleGenaiLLM()
    return embedder, reranker, llm


def build_context(
    selection: AdapterSelection,
    settings: Settings,
    *,
    chunks: Sequence[Chunk] = (),
    clock: Clock | None = None,
    chunk_source: ChunkSource | None = None,
    conditional_headers_for: Callable[[str], Mapping[str, str]] | None = None,
    http_client: httpx.Client | None = None,
) -> IntegrationContext:
    """Compose the real pipeline from the selected adapters."""
    selected_clock: Clock = SystemClock() if selection.clock == "system" else (clock or FakeClock())
    if selection.clock == "fake" and clock is not None:
        selected_clock = clock
    fetcher = build_fetcher(
        selection,
        settings,
        conditional_headers_for=conditional_headers_for,
        client=http_client,
    )
    object_store = build_object_store(selection, settings)
    vector_store = build_vector_store(selection, settings, clock=selected_clock)
    build_metadata_store(selection, settings, clock=selected_clock)
    embedder, reranker, llm = build_providers(selection, settings)
    source = chunk_source if chunk_source is not None else _ChunkSource(chunks)
    pipeline = RetrievalPipeline(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
        reranker=reranker,
        llm=llm,
        clock=selected_clock,
        chunk_source=source if chunks else None,
        search_mode=SearchMode.HYBRID,
        rerank_enabled=True,
        freshness_boost_enabled=False,
    )
    return IntegrationContext(
        selection=selection,
        settings=settings,
        clock=selected_clock,
        fetcher=fetcher,
        object_store=object_store,
        vector_store=vector_store,
        embedder=embedder,
        reranker=reranker,
        llm=llm,
        pipeline=pipeline,
        chunk_source=source if chunks else None,
    )


def fixture_path(registry_path: Path, source_path: str) -> Path:
    """Resolve a registry-relative fixture path without touching the network."""
    return (registry_path.resolve().parents[2] / source_path).resolve()
