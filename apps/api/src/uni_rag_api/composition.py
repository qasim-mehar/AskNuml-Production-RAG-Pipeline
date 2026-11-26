"""Backend composition: fake by default, the public retrieval pipeline behind the flag.

Lane E arrives only through :class:`uni_rag_retrieval.service.RetrievalPipeline`
and core ports (L2, L14). Provider SDKs are never imported here; live adapters
are constructed lazily inside the branches that opt in (L3, ADR 0008). The
papers finder always reads Lane D's parsed-record store through the API-local
``PapersProvider`` port; only the store's backing differs by backend (ADR 0011).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from uni_rag_api.fixtures import IMAGE_BYTES, IMAGE_CONTENT_TYPES, LAST_CRAWLED, PAPER_RECORDS
from uni_rag_api.ports import AnswerService, PaperRecordStore, PapersProvider
from uni_rag_api.service import FakeAnswerService, StoredPapersProvider, seed_paper_records
from uni_rag_core import (
    LLM,
    ApiSection,
    ConfigError,
    Embedder,
    FakeEmbedder,
    FakeLLM,
    FakeObjectStore,
    FakeReranker,
    FakeVectorStore,
    ObjectStore,
    ProvidersSection,
    Reranker,
    Settings,
    VectorStore,
    get_logger,
)
from uni_rag_core.schemas import Chunk, DocType
from uni_rag_indexing.domain.metadata_memory import InMemoryMetadataStore
from uni_rag_retrieval.service import RetrievalPipeline

if TYPE_CHECKING:
    from uni_rag_core import Answer, Clock, Query

_log = get_logger("uni_rag_api.composition")


class Backend(StrEnum):
    """Which answer service the API composes."""

    FAKE = "fake"
    REAL = "real"


def ephemeral_settings(
    *,
    api: ApiSection | None = None,
    providers: ProvidersSection | None = None,
) -> Settings:
    """Build env-free, deterministic settings for embedding and tests.

    The deployed entry point uses core ``get_settings`` and still fails fast on
    missing infrastructure (L8); this helper exists so schema generation and
    in-process tests never need a real Qdrant, Postgres or MinIO.
    """
    return Settings(
        qdrant_url="http://qdrant.invalid:6333",
        postgres_dsn="postgresql://uni-rag:uni-rag@postgres.invalid:5432/uni_rag",
        minio_endpoint="http://minio.invalid:9000",
        api=api if api is not None else ApiSection(),
        providers=providers if providers is not None else ProvidersSection(),
    )


def resolve_backend(settings: Settings, backend: Backend | None = None) -> Backend:
    """Derive the backend from the ADR 0008 live flag unless explicitly overridden."""
    if backend is not None:
        return backend
    return Backend.REAL if settings.providers.live_enabled else Backend.FAKE


@dataclass(frozen=True)
class PipelinePorts:
    """Optional injected ports for the real composition; fakes fill the gaps."""

    embedder: Embedder | None = None
    vector_store: VectorStore | None = None
    reranker: Reranker | None = None
    llm: LLM | None = None


@dataclass(frozen=True)
class BackendBundle:
    """The services the app stores on state for both backends."""

    backend: Backend
    answer_service: AnswerService
    object_store: ObjectStore
    papers_provider: PapersProvider
    paper_record_store: PaperRecordStore


class PipelineAnswerService:
    """Adapt Lane E's public pipeline to the API's synchronous port (L3)."""

    def __init__(self, pipeline: RetrievalPipeline) -> None:
        self._pipeline = pipeline

    def answer(self, query: Query) -> Answer:
        """Run the pipeline; ADR 0007 fields pass through untouched (L5)."""
        return self._pipeline.run(query)

    def tokens(self, answer: Answer) -> Iterator[str]:
        """Yield space-delimited tokens that rejoin to ``answer.text``."""
        yield from answer.text.split(" ")


def seeded_fake_object_store() -> FakeObjectStore:
    """Return the deterministic fake store used by fake and injected-real tests."""
    store = FakeObjectStore()
    for key, data in IMAGE_BYTES.items():
        store.put(key, data, content_type=IMAGE_CONTENT_TYPES[key])
    return store


def seeded_paper_record_store() -> PaperRecordStore:
    """Seed an in-memory parsed-record store from fixture-derived records (L4, ADR 0011).

    Deterministic fake mode only. The live backend reads the persisted Postgres
    table instead and is never seeded from fixtures here.
    """
    store = InMemoryMetadataStore()
    seed_paper_records(store, PAPER_RECORDS, indexed_at=LAST_CRAWLED)
    return store


def seeded_pipeline_ports(*, dimension: int = 16) -> PipelinePorts:
    """Deterministic "real" composition made entirely of core fakes (L4)."""
    from uni_rag_api.fixtures import LAST_CRAWLED

    vector_store = FakeVectorStore()
    chunk = Chunk(
        chunk_id="chunk-real-001",
        doc_id="doc-cs101",
        source_url="https://example.edu/courses/cs101/assessment",
        heading_path=["Assessment"],
        content_hash="fake-hash-cs101",
        last_crawled=LAST_CRAWLED,
        doc_type=DocType.WEB_PAGE,
        version="1",
        text="The midterm exam contributes 40 percent to the final grade.",
        language="en",
    )
    vector_store.upsert([(chunk, [0.0] * (dimension - 1) + [1.0])])
    return PipelinePorts(
        embedder=FakeEmbedder(dimension=dimension),
        vector_store=vector_store,
        reranker=FakeReranker(),
        llm=FakeLLM(),
    )


def _real_object_store(settings: Settings, *, live: bool) -> ObjectStore:
    """Select the object store from settings; the SDK stays inside its adapter."""
    if not live:
        return seeded_fake_object_store()
    from uni_rag_indexing.adapters.minio_object_store import MinioObjectStore

    return MinioObjectStore.from_settings(settings)


def _real_pipeline(
    settings: Settings, *, clock: Clock, ports: PipelinePorts, live: bool
) -> RetrievalPipeline:
    """Compose only core ports plus Lane E's public service (L2, L3, L17)."""
    if live and (ports.embedder is None or ports.llm is None):
        raise ConfigError(
            "Live provider mode requires injected Embedder and LLM adapters.",
            context={"live_enabled": True},
        )

    embedder: Embedder = (
        ports.embedder
        if ports.embedder is not None
        else FakeEmbedder(dimension=settings.embedding_dimension)
    )
    llm: LLM = ports.llm if ports.llm is not None else FakeLLM()
    reranker: Reranker = ports.reranker if ports.reranker is not None else FakeReranker()

    if ports.vector_store is not None:
        vector_store: VectorStore = ports.vector_store
    elif live:
        from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore

        vector_store = QdrantVectorStore.from_settings(settings, clock=clock)
    else:
        vector_store = FakeVectorStore()

    return RetrievalPipeline(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
        reranker=reranker,
        llm=llm,
        clock=clock,
    )


def build_backend(
    settings: Settings,
    *,
    clock: Clock,
    backend: Backend | None = None,
    ports: PipelinePorts | None = None,
    object_store: ObjectStore | None = None,
    answer_service: AnswerService | None = None,
    papers_provider: PapersProvider | None = None,
    paper_record_store: PaperRecordStore | None = None,
) -> BackendBundle:
    """Resolve the flag and wire answer/image services with fakes as the default.

    The papers finder is store-backed on both backends (ADR 0011): fake mode
    seeds an in-memory parsed-record store from fixtures, while live mode reads
    Lane D's Postgres table. Injecting a store or a provider keeps tests
    deterministic without changing the route contract (L1, L3, L4).
    """
    resolved = resolve_backend(settings, backend)
    live = resolved is Backend.REAL and settings.providers.live_enabled
    store = object_store if object_store is not None else _real_object_store(settings, live=live)

    if answer_service is not None:
        service = answer_service
    elif resolved is Backend.FAKE:
        service = FakeAnswerService()
    else:
        service = PipelineAnswerService(
            _real_pipeline(settings, clock=clock, ports=ports or PipelinePorts(), live=live)
        )

    papers_store = paper_record_store
    if papers_store is None:
        if live:
            from uni_rag_indexing.adapters.postgres_metadata_store import PostgresMetadataStore

            papers_store = PostgresMetadataStore.from_settings(settings, clock=clock)
        else:
            papers_store = seeded_paper_record_store()
    resolved_papers = (
        papers_provider if papers_provider is not None else StoredPapersProvider(papers_store)
    )
    _log.info(
        "backend.selected",
        backend=resolved.value,
        live_providers=live,
        papers_provider=type(resolved_papers).__name__,
        papers_store=type(papers_store).__name__,
    )
    return BackendBundle(
        backend=resolved,
        answer_service=service,
        object_store=store,
        papers_provider=resolved_papers,
        paper_record_store=papers_store,
    )


__all__ = [
    "Backend",
    "BackendBundle",
    "PipelineAnswerService",
    "PipelinePorts",
    "PapersProvider",
    "build_backend",
    "seeded_paper_record_store",
    "ephemeral_settings",
    "resolve_backend",
    "seeded_fake_object_store",
    "seeded_pipeline_ports",
]
