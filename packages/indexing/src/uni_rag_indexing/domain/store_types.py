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

from uni_rag_core import Chunk, Document, ImageRef, PastPaperQuestion, StorageError
from uni_rag_indexing.domain.filters import ensure_aware


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


@dataclass(frozen=True)
class ParsedPaperRecord:
    """A parsed past-paper question with provenance frozen at write time (ADR 0011).

    This is the relational view of the API's ``PaperRecord``: the ADR 0007 finder
    fields plus ``last_crawled``. Page images stay in ``ObjectStore``; only the
    resolvable ``ImageRef`` is stored here. No enrichment, embedding or
    operational filter state is part of this datum (ADR 0010).
    """

    question_id: str
    doc_id: str
    source_url: str
    page: int
    question_number: int
    text: str
    last_crawled: datetime
    year: int | None = None
    subject: str | None = None
    options: tuple[str, ...] = ()
    image_ref: ImageRef | None = None
    course_code: str | None = None
    term: str | None = None
    exam_type: str | None = None
    department: str | None = None

    @classmethod
    def from_question(
        cls, question: PastPaperQuestion, *, last_crawled: datetime
    ) -> ParsedPaperRecord:
        """Freeze a parser's question and its crawl timestamp into one record."""
        return cls(
            question_id=question.question_id,
            doc_id=question.doc_id,
            source_url=question.source_url,
            page=question.page,
            question_number=question.question_number,
            text=question.text,
            last_crawled=ensure_aware(last_crawled, field="last_crawled"),
            year=question.year,
            subject=question.subject,
            options=tuple(question.options),
            image_ref=question.image_ref,
            course_code=question.course_code,
            term=question.term,
            exam_type=question.exam_type,
            department=question.department,
        )

    def to_question(self) -> PastPaperQuestion:
        """Return the ADR 0007 finder fields carried by this stored record."""
        return PastPaperQuestion(
            question_id=self.question_id,
            doc_id=self.doc_id,
            source_url=self.source_url,
            page=self.page,
            question_number=self.question_number,
            text=self.text,
            year=self.year,
            subject=self.subject,
            options=list(self.options),
            image_ref=self.image_ref,
            course_code=self.course_code,
            term=self.term,
            exam_type=self.exam_type,
            department=self.department,
        )


@dataclass(frozen=True)
class PaperRecordFilters:
    """Domain-local conjunction of the five finder axes plus bounded pagination."""

    course_code: str | None = None
    year: int | None = None
    term: str | None = None
    exam_type: str | None = None
    department: str | None = None
    limit: int = 20
    offset: int = 0


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

    def upsert_paper_record(
        self, record: ParsedPaperRecord, *, ordinal: int, indexed_at: datetime
    ) -> None:
        """Persist a parsed record with its provenance frozen at write time."""
        ...

    def find_paper_records(self, filters: PaperRecordFilters) -> Sequence[ParsedPaperRecord]:
        """Return matching parsed records in stable ordinal order, then paginate."""
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
