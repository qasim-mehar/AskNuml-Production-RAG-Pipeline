"""Domain-local store protocols and typed storage errors.

A DocumentStore/ChunkStore port is deliberately *not* added to ``core``:
these Protocols stay local until a CONTRACT-CHANGE PR is accepted by Lane 0.
The error subclasses extend the frozen ``StorageError`` hierarchy so callers
can keep catching one base type (L11).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from uni_rag_core import Chunk, Document, StorageError


class StorageConnectionError(StorageError):
    """A store could not be reached; ``context['host']`` names the endpoint."""


class StorageNotFoundError(StorageError):
    """A requested record or object does not exist."""


class StorageConflictError(StorageError):
    """A write collided with an existing, different record."""


@dataclass(frozen=True)
class ChunkRecord:
    """One version of a chunk as persisted in the relational metadata store."""

    chunk_id: str
    doc_id: str
    version: str
    content_hash: str
    payload: dict[str, Any]
    indexed_at: datetime
    deleted_at: datetime | None = None
    superseded_by: str | None = None

    @property
    def is_live(self) -> bool:
        """Return True while this version has not been soft-deleted."""
        return self.deleted_at is None


@dataclass(frozen=True)
class CrawlState:
    """The last successful crawl for one source document."""

    doc_id: str
    last_crawled: datetime
    content_hash: str
    status: str
    attempts: int
    error: str | None
    updated_at: datetime


@runtime_checkable
class MetadataStore(Protocol):
    """Read/write access to documents, chunk versions and crawl state."""

    def upsert_document(self, document: Document, *, indexed_at: datetime) -> None:
        """Insert a document or leave an identical one untouched."""
        ...

    def get_document(self, doc_id: str) -> Document | None:
        """Return the document with ``doc_id`` or None."""
        ...

    def get_chunk(self, chunk_id: str) -> ChunkRecord | None:
        """Return the newest version of a chunk, including soft-deleted rows."""
        ...

    def upsert_chunk(self, chunk: Chunk, *, indexed_at: datetime) -> ChunkRecord:
        """Insert a chunk version, preserving identical data and rejecting conflicts."""
        ...

    def soft_delete_chunk(
        self, chunk_id: str, *, deleted_at: datetime, superseded_by: str | None = None
    ) -> None:
        """Mark every live version of a chunk as stale; never drop the row."""
        ...

    def list_live_chunk_ids(self, doc_id: str) -> Sequence[str]:
        """Return ids of all non-deleted chunks belonging to ``doc_id``."""
        ...

    def list_chunk_history(self, doc_id: str) -> Sequence[ChunkRecord]:
        """Return every version, including soft-deleted ones, for history tooling."""
        ...

    def upsert_crawl_state(self, state: CrawlState) -> None:
        """Persist the latest crawl outcome for a document."""
        ...

    def get_crawl_state(self, doc_id: str) -> CrawlState | None:
        """Return the stored crawl state or None."""
        ...


@runtime_checkable
class VersionedVectorStore(Protocol):
    """Optional capability implemented by the Qdrant adapter and test fakes."""

    def mark_stale(self, chunk_id: str, *, superseded_by: str, deleted_at: datetime) -> None:
        """Soft-delete live vectors for a chunk id, keeping them queryable by history."""
        ...

    def is_present(self, chunk_id: str) -> bool:
        """Return True when a live point exists for ``chunk_id``."""
        ...


@dataclass(frozen=True)
class IndexResult:
    """Counts returned by one indexing run; used for measurement, not assertion."""

    inserted: int = 0
    unchanged: int = 0
    updated: int = 0
    stale_soft_deleted: int = 0
    images_stored: int = 0
    verified: int = 0

    @property
    def total(self) -> int:
        """Return the number of input chunks considered."""
        return self.inserted + self.unchanged + self.updated
