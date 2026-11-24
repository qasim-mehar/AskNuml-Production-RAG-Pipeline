"""Deterministic fixture corpus driven by the golden set (L4, L12).

The shared `mini-golden.json` is read-only and lives at the workspace root.
Every chunk here is fabricated fixture data; no live site or provider is used.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from uni_rag_core import (
    Chunk,
    DocType,
    FakeClock,
    FakeEmbedder,
    FakeLLM,
    FakeReranker,
    FakeVectorStore,
    ImageRef,
    Language,
    Query,
    Settings,
)
from uni_rag_retrieval.domain.fusion import ChunkSource, SearchMode
from uni_rag_retrieval.service import RetrievalPipeline

FIXED_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
OLD_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
_GOLDEN = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "golden" / "mini-golden.json"

_COURSE_URL = "https://example.edu/courses/cs101"
_ANNOUNCEMENTS_URL = "https://example.edu/news/announcements-2026"
_FACULTY_URL = "https://example.edu/directory/faculty"
_CAMPUS_URL = "https://example.edu/campus/services"


def golden_queries() -> list[dict[str, Any]]:
    """Load the ten read-only golden queries."""
    return json.loads(_GOLDEN.read_text(encoding="utf-8"))


def golden_query(row: dict[str, Any], *, top_k: int = 10) -> Query:
    """Turn a golden row into a frozen Query."""
    return Query(
        query_id=row["id"],
        text=row["query"],
        language=Language(row["language"]),
        top_k=top_k,
    )


def _chunk(
    chunk_id: str,
    doc_id: str,
    source_url: str,
    text: str,
    *,
    page: int | None = 1,
    language: Language = Language.EN,
    last_crawled: datetime = FIXED_TIME,
    heading_path: list[str] | None = None,
    image_ref: ImageRef | None = None,
    doc_type: DocType = DocType.WEB_PAGE,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        source_url=source_url,
        heading_path=heading_path or [doc_id],
        content_hash=f"hash-{chunk_id}",
        last_crawled=last_crawled,
        doc_type=doc_type,
        version="1",
        text=text,
        page=page,
        language=language,
        image_ref=image_ref,
    )


def build_corpus() -> list[Chunk]:
    """Return one matching chunk set per golden row plus abstention/freshness pairs."""
    course_image = ImageRef(
        ref_id="images/doc-cs101-outline/p1.png",
        source_url=_COURSE_URL,
        page=1,
        caption="CS-101 outline page 1",
    )
    return [
        _chunk(
            "chunk-cs101-instructor",
            "doc-cs101-outline",
            _COURSE_URL,
            "CS-101 instructor is Dr. Ayesha Khan. Office hours on request.",
            heading_path=["CS-101", "Instructor"],
            image_ref=course_image,
        ),
        _chunk(
            "chunk-cs101-credits",
            "doc-cs101-outline",
            _COURSE_URL,
            "CS-101 is worth 4 credits and is offered in the fall term.",
            heading_path=["CS-101", "Credits"],
        ),
        _chunk(
            "chunk-cs101-outcomes",
            "doc-cs101-outline",
            _COURSE_URL,
            "CS-101 learning outcomes: Write and debug programs in Python.",
            heading_path=["CS-101", "Outcomes"],
        ),
        _chunk(
            "chunk-cs101-instructor-ur",
            "doc-cs101-outline",
            _COURSE_URL,
            "CS-101 کے انسٹرکٹر ڈاکٹر عائشہ خان ہیں۔",
            language=Language.UR,
        ),
        _chunk(
            "chunk-cs101-credits-ur",
            "doc-cs101-outline",
            _COURSE_URL,
            "CS-101 4 کریڈٹس کا کورس ہے۔",
            language=Language.UR,
        ),
        _chunk(
            "chunk-cs101-instructor-roman",
            "doc-cs101-outline",
            _COURSE_URL,
            "CS-101 ka instructor Dr. Ayesha Khan hai.",
            language=Language.ROMAN_URDU,
        ),
        _chunk(
            "chunk-ann-midterm",
            "doc-announcements-2026",
            _ANNOUNCEMENTS_URL,
            "CS-101 midterm exam is on October 17, 2026.",
            heading_path=["Announcements", "Midterm"],
        ),
        _chunk(
            "chunk-ann-midterm-roman",
            "doc-announcements-2026",
            _ANNOUNCEMENTS_URL,
            "CS-101 ka midterm 17 October 2026 ko hai.",
            language=Language.ROMAN_URDU,
        ),
        _chunk(
            "chunk-ann-orientation",
            "doc-announcements-2026",
            _ANNOUNCEMENTS_URL,
            "New student orientation begins August 24, 2026.",
        ),
        _chunk(
            "chunk-faculty",
            "doc-faculty-directory",
            _FACULTY_URL,
            "Computer science faculty research interests include information retrieval and NLP.",
        ),
        _chunk(
            "chunk-weak-parking",
            "doc-campus",
            _CAMPUS_URL,
            "Campus map and building hours are available at the office.",
            page=None,
        ),
        _chunk(
            "chunk-fresh-new",
            "doc-freshness",
            "https://example.edu/freshness",
            "Freshness policy reference note.",
            page=None,
        ),
        _chunk(
            "chunk-fresh-old",
            "doc-freshness",
            "https://example.edu/freshness",
            "Freshness policy reference note.",
            page=None,
            last_crawled=OLD_TIME,
        ),
    ]


def settings_for_tests(**overrides: Any) -> Settings:
    """Build typed settings explicitly; no environment reads (L8)."""
    values: dict[str, Any] = {
        "qdrant_url": "http://localhost:6333",
        "postgres_dsn": "postgresql://user:pass@localhost/uni_rag",
        "minio_endpoint": "http://localhost:9000",
        "embedding_dimension": 16,
        "default_top_k": 10,
        "abstention_threshold": 0.35,
    }
    values.update(overrides)
    return Settings(**values)


def indexed_store(corpus: list[Chunk] | None = None) -> FakeVectorStore:
    """Upsert the fixture corpus into a deterministic fake vector store."""
    store = FakeVectorStore()
    embedder = FakeEmbedder(dimension=16)
    chunks = corpus if corpus is not None else build_corpus()
    store.upsert([(chunk, embedder.embed([chunk.text])[0]) for chunk in chunks])
    return store


def make_pipeline(
    *,
    corpus: list[Chunk] | None = None,
    search_mode: SearchMode = SearchMode.HYBRID,
    rerank_enabled: bool = True,
    freshness_boost_enabled: bool = True,
    chunk_source: ChunkSource | None = None,
    **settings_overrides: Any,
) -> RetrievalPipeline:
    """Build a fully faked pipeline with named ablation axes (L4)."""
    return RetrievalPipeline(
        settings=settings_for_tests(**settings_overrides),
        embedder=FakeEmbedder(dimension=16),
        vector_store=indexed_store(corpus),
        reranker=FakeReranker(),
        llm=FakeLLM(),
        clock=FakeClock(FIXED_TIME),
        chunk_source=chunk_source,
        search_mode=search_mode,
        rerank_enabled=rerank_enabled,
        freshness_boost_enabled=freshness_boost_enabled,
    )


WEAK_QUERY = Query(
    query_id="weak-01", text="What is the parking fee for students?", language=Language.EN
)
