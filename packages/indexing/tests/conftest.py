"""Fixtures for indexing lanes tests (L4/L12). Fixtures come before behaviour."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from qdrant_client import QdrantClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tests.factories import FIXED_TIME, chunk
from uni_rag_core import Chunk, DocType, FakeClock, FakeEmbedder
from uni_rag_indexing.adapters.minio_object_store import MinioObjectStore
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore
from uni_rag_indexing.domain.fakes import FakeMinioClient
from uni_rag_indexing.domain.metadata_memory import InMemoryMetadataStore
from uni_rag_indexing.domain.payload_index import PayloadVectorIndex

LATER = FIXED_TIME + timedelta(days=1)


def pytest_configure(config: pytest.Config) -> None:
    """Register the integration marker without touching root config."""
    config.addinivalue_line(
        "markers", "integration: requires live compose services or a local store"
    )


@pytest.fixture
def fixed_clock() -> FakeClock:
    return FakeClock(FIXED_TIME)


@pytest.fixture
def later_clock() -> FakeClock:
    return FakeClock(LATER)


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder(dimension=16)


@pytest.fixture
def base_chunk() -> Chunk:
    return chunk()


@pytest.fixture
def corpus() -> list[Chunk]:
    """One chunk per doc_type, one image-bearing chunk and one exact duplicate."""
    base = chunk()
    pdf = base.model_copy(
        update={
            "chunk_id": "chunk-2",
            "doc_id": "doc-2",
            "doc_type": DocType.PDF,
            "content_hash": "hash-chunk-2",
            "source_url": "https://example.edu/papers/cs201-fall-2024.pdf",
            "heading_path": ["CS-201", "Fall 2024", "Lecture 1"],
            "image_ref": None,
            "page": 4,
        }
    )
    paper = base.model_copy(
        update={
            "chunk_id": "chunk-3",
            "doc_id": "doc-3",
            "doc_type": DocType.PAST_PAPER,
            "content_hash": "hash-chunk-3",
            "source_url": "https://example.edu/papers/2025-final.pdf",
            "heading_path": ["CS-101", "Spring 2025", "Past Paper"],
            "image_ref": None,
        }
    )
    other = base.model_copy(
        update={
            "chunk_id": "chunk-4",
            "doc_id": "doc-4",
            "doc_type": DocType.OTHER,
            "content_hash": "hash-chunk-4",
            "source_url": "https://example.edu/notes/misc.html",
            "heading_path": ["Notes"],
            "image_ref": None,
        }
    )
    return [base, pdf, paper, other, base]  # last entry is the idempotency duplicate


@pytest.fixture
def stale_pair() -> tuple[Chunk, Chunk]:
    """The same chunk id with new text: version bumps, old version goes stale."""
    original = chunk().model_copy(update={"chunk_id": "chunk-5", "doc_id": "doc-5"})
    changed = original.model_copy(
        update={"content_hash": "hash-chunk-5-v2", "version": "2", "text": "Updated policy text."}
    )
    return original, changed


@pytest.fixture
def payload_index(fixed_clock: FakeClock) -> PayloadVectorIndex:
    return PayloadVectorIndex(clock=fixed_clock)


@pytest.fixture
def qdrant_local(fixed_clock: FakeClock) -> QdrantVectorStore:
    """Live Qdrant client in local mode: no Docker, real filtering semantics."""
    return QdrantVectorStore(QdrantClient(":memory:"), dimension=16, clock=fixed_clock)


@pytest.fixture
def qdrant_contract(fixed_clock: FakeClock) -> QdrantVectorStore:
    """2-D collection for the shared VectorStore contract suite."""
    return QdrantVectorStore(QdrantClient(":memory:"), dimension=2, clock=fixed_clock)


@pytest.fixture
def minio_store() -> MinioObjectStore:
    """Adapter over an in-memory MinIO client double."""
    return MinioObjectStore(FakeMinioClient(), bucket="uni-rag", host="minio")


@pytest.fixture
def metadata_memory() -> InMemoryMetadataStore:
    return InMemoryMetadataStore()


@pytest.fixture
def sqlite_engine() -> object:
    """In-memory SQLite engine with a static pool for migration tests."""
    return create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )


@pytest.fixture
def fixed_time() -> datetime:
    """Return the canonical UTC timestamp used by every fixture."""
    return FIXED_TIME.astimezone(UTC)
