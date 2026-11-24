"""End-to-end smoke over the fixture corpus, composed from real adapters (L5, L12).

The compose-backed test skips when the services are absent. The fetcher test
uses only a local test server and therefore exercises Lane A's real adapter on
every host.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast

import httpx
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from minio import Minio
from qdrant_client import QdrantClient

from tests.contracts.port_contracts import (
    assert_object_store_contract,
    assert_vector_store_contract,
)
from tests.factories import document as sample_document
from tests.integration.composition import (
    build_context,
    build_fetcher,
    build_metadata_store,
    build_parser,
    fixture_path,
)
from tests.integration.doubles import MemoryMinioClient
from tests.integration.provenance import attach_provenance
from tests.integration.selection import AdapterSelection
from uni_rag_core import (
    Answer,
    Chunk,
    Document,
    FakeClock,
    ImageRef,
    Language,
    ObjectStore,
    Query,
    Settings,
    SystemClock,
    VectorStore,
)
from uni_rag_indexing.adapters.minio_object_store import MinioObjectStore
from uni_rag_indexing.adapters.postgres_metadata_store import PostgresMetadataStore
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore
from uni_rag_ingestion.chunking.domain.model import Block, BlockKind
from uni_rag_ingestion.chunking.domain.model import ParsedDocument as ChunkableDocument
from uni_rag_ingestion.chunking.domain.strategy_fixed_window import STRATEGY_NAME as FIXED_WINDOW
from uni_rag_ingestion.chunking.domain.strategy_sentence import STRATEGY_NAME as SENTENCE_BOUNDARY
from uni_rag_ingestion.chunking.service.chunk import Chunker
from uni_rag_ingestion.crawler.adapters.http_fetcher import HttpFetcher
from uni_rag_ingestion.crawler.domain import CrawlerConfig
from uni_rag_ingestion.crawler.service.crawl import CrawlService
from uni_rag_ingestion.parsers.adapters.docling_parser import DoclingParser
from uni_rag_ingestion.parsers.domain.models import ParsedPage, ParsedTable
from uni_rag_ingestion.parsers.service.parse import parse_document

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "ingestion"
    / "tests"
    / "crawler"
    / "fixtures"
    / "html"
)
_REGISTRY = Path(__file__).resolve().parents[2] / "eval" / "golden" / "fixture-registry.json"

_GOLDEN_QUERIES: tuple[tuple[str, Language, bool], ...] = (
    ("Who is the instructor for CS-101?", Language.EN, False),
    ("CS-101 کے انسٹرکٹر کون ہیں؟", Language.UR, False),
    ("CS-101 ka instructor kaun hai?", Language.ROMAN_URDU, False),
    ("What is the tuition fee for CS-101?", Language.EN, True),
)


class _FixtureHandler(SimpleHTTPRequestHandler):
    """Serve checked-in crawler fixtures plus deterministic conditional/redirect cases."""

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        """Answer fixture requests without touching the live university site."""
        if self.path == "/conditional":
            body = b"<html><body>Conditional page.</body></html>"
            self.send_response(200 if self.headers.get("If-None-Match") != '"fixture-v1"' else 304)
            self.send_header("ETag", '"fixture-v1"')
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.headers.get("If-None-Match") != '"fixture-v1"' and self.command != "HEAD":
                self.wfile.write(body)
            return
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/content-v1.html")
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, format: str, *args: object) -> None:
        """Route access logs nowhere; the core structured logger handles tracing."""


@contextmanager
def _local_fixture_server() -> Iterator[str]:
    """Serve the fixture directory on localhost and yield its base URL."""
    handler = partial(_FixtureHandler, directory=str(_FIXTURE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_fetcher_swap_uses_real_http_fetcher(integration_settings: Settings) -> None:
    """Lane A's fetcher honours user agent, redirects and conditional headers."""
    assert AdapterSelection.ci_default().fetcher == "fake"
    selection = AdapterSelection.from_settings(integration_settings)
    assert selection.fetcher == "http"

    with _local_fixture_server() as base, httpx.Client(timeout=5) as client:
        fetcher = cast(
            HttpFetcher,
            build_fetcher(
                selection,
                integration_settings,
                client=client,
                conditional_headers_for=lambda url: (
                    {"If-None-Match": '"fixture-v1"'} if url.endswith("/conditional") else {}
                ),
            ),
        )
        fetched = fetcher.fetch(f"{base}/content-v1.html")
        assert fetched.status_code == 200
        assert fetched.final_url.endswith("/content-v1.html")
        assert fetcher.last_request_headers["User-Agent"] == integration_settings.crawler.user_agent

        redirected = fetcher.fetch(f"{base}/redirect")
        assert redirected.status_code == 200
        assert redirected.final_url.endswith("/content-v1.html")

        conditional = fetcher.fetch(f"{base}/conditional")
        assert conditional.status_code == 304
        assert conditional.body == b""


def _source_path(document: Document, registry_path: Path) -> Path:
    """Map a crawled document back to its checked-in fixture source."""
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    for entry in payload["documents"]:
        if entry["source_url"] == document.source_url:
            return fixture_path(registry_path, entry["source_path"])
    raise AssertionError(f"no fixture maps to {document.source_url!r}")


def _chunkable(
    document: Document,
    pages: tuple[ParsedPage, ...],
    image_refs: Mapping[int, ImageRef],
) -> ChunkableDocument:
    """Translate Lane B's pages into Lane C's ordered block vocabulary."""
    blocks: list[Block] = []
    for page in pages:
        lines = [line for line in page.text.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            blocks.append(
                Block(
                    kind=BlockKind.HEADING if index == 0 else BlockKind.PARAGRAPH,
                    text=line,
                    index=len(blocks),
                    level=1 if index == 0 else 0,
                    page=page.page,
                    image_ref=image_refs.get(page.page),
                )
            )
        for table in page.tables:
            blocks.append(
                Block(
                    kind=BlockKind.TABLE,
                    text="",
                    index=len(blocks),
                    table_rows=_rows(table),
                    page=page.page,
                    image_ref=image_refs.get(page.page),
                )
            )
    return ChunkableDocument(document=document, blocks=tuple(blocks))


def _rows(table: ParsedTable) -> tuple[tuple[str, ...], ...]:
    """Return a table as header-plus-rows cells."""
    return (table.header, *table.rows)


def test_parser_swap_uses_docling_adapter(integration_settings: Settings) -> None:
    """Lane B's adapter is real; Docling's absence uses the sanctioned reader."""
    assert AdapterSelection.ci_default().parser == "fixture"
    selection = AdapterSelection.from_settings(integration_settings)
    assert selection.parser == "docling"
    parser = build_parser(selection)
    assert isinstance(parser, DoclingParser)
    parsed = parser.parse(_FIXTURE_DIR / "content-v1.html")
    assert parsed.pages and parsed.pages[0].text


def test_clock_swap_uses_system_clock_in_pipeline(integration_settings: Settings) -> None:
    """Production config uses SystemClock; CI default and pinned tests stay fake."""
    assert AdapterSelection.from_settings(integration_settings).clock == "system"
    clock_only = replace(AdapterSelection.ci_default(), clock="system")
    assert isinstance(build_context(clock_only, integration_settings).clock, SystemClock)

    pinned = build_context(AdapterSelection.ci_default(), integration_settings, clock=FakeClock())
    assert isinstance(pinned.clock, FakeClock)


def test_metadata_swap_uses_postgres_adapter_and_linear_history(
    integration_settings: Settings,
) -> None:
    """The Postgres adapter is selected and Alembic has one linear head."""
    selection = AdapterSelection.from_settings(integration_settings)
    assert selection.metadata == "postgres"
    store = build_metadata_store(selection, integration_settings, clock=SystemClock())
    assert isinstance(store, PostgresMetadataStore)

    config = Config(str(_REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(_REPO_ROOT / "infra" / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert len(script.get_heads()) == 1


def test_object_store_swap_uses_minio_adapter(integration_settings: Settings) -> None:
    """Lane D's real MinIO adapter passes the shared ObjectStore contract."""
    selection = AdapterSelection.from_settings(integration_settings)
    assert selection.object_store == "minio"
    store = MinioObjectStore(cast(Minio, MemoryMinioClient()), bucket="uni-rag", host="minio")
    assert isinstance(store, ObjectStore)
    assert_object_store_contract(store)


def test_vector_store_swap_uses_qdrant_adapter(integration_settings: Settings) -> None:
    """Lane D's real adapter passes the shared VectorStore contract."""
    selection = AdapterSelection.from_settings(integration_settings)
    assert selection.vector_store == "qdrant"
    store = QdrantVectorStore(QdrantClient(":memory:"), dimension=2, host="in-memory")
    assert isinstance(store, VectorStore)
    assert_vector_store_contract(store)


def test_chunking_swap_runs_both_strategies(integration_settings: Settings) -> None:
    """Both Lane C strategies chunk the same fixture deterministically."""
    selection = AdapterSelection.from_settings(integration_settings)
    assert selection.chunking == "strategies"
    parsed = build_parser(selection).parse(_FIXTURE_DIR / "content-v1.html")
    chunkable = _chunkable(sample_document(), parsed.pages, {})
    for strategy in (FIXED_WINDOW, SENTENCE_BOUNDARY):
        first = Chunker(strategy).chunk(chunkable)
        second = Chunker(strategy).chunk(chunkable)
        assert first and first == second


@pytest.mark.integration
def test_integrated_pipeline_smoke(
    skip_without_compose: None,
    integration_settings: Settings,
) -> None:
    """Crawl, parse, chunk, index and answer with provenance on every citation."""
    with _local_fixture_server() as base, httpx.Client(timeout=10) as client:
        selection = AdapterSelection.from_settings(integration_settings)
        assert selection.parser == "docling"
        assert selection.vector_store == "qdrant"
        assert selection.object_store == "minio"
        assert selection.metadata == "postgres"
        assert selection.clock == "system"

        config = CrawlerConfig(
            seeds=(f"{base}/content-v1.html", f"{base}/pdf-links-page.html"),
            max_depth=1,
            requests_per_second=1000.0,
        )
        crawler = CrawlService(
            config,
            build_fetcher(selection, integration_settings, client=client),
            SystemClock(),
        )
        report = crawler.run()
        assert report.documents

        ctx = build_context(selection, integration_settings)
        parser = build_parser(selection)
        all_chunks: dict[str, Chunk] = {}
        for strategy in (FIXED_WINDOW, SENTENCE_BOUNDARY):
            chunker = Chunker(strategy)
            for document in report.documents:
                outcome = parse_document(
                    document,
                    source_path=_source_path(document, _REGISTRY),
                    parser=parser,
                    object_store=ctx.object_store,
                )
                parsed = parser.parse(_source_path(document, _REGISTRY))
                chunkable = _chunkable(document, parsed.pages, outcome.image_refs)
                for chunk in chunker.chunk(chunkable):
                    all_chunks[chunk.chunk_id] = chunk
        assert len(all_chunks) > 0
        ctx.vector_store.upsert(
            [(chunk, ctx.embedder.embed([chunk.text])[0]) for chunk in all_chunks.values()]
        )

        for index, (text, language, weak) in enumerate(_GOLDEN_QUERIES):
            answer: Answer = ctx.ask(
                Query(query_id=f"smoke-{index}", text=text, language=language, top_k=5)
            )
            answer = attach_provenance(answer, all_chunks, language)
            if weak:
                assert answer.abstained
                assert answer.next_step
            else:
                assert answer.citations
                for citation in answer.citations:
                    assert citation.source_url
                    assert citation.last_crawled is not None
            assert answer.language == language
