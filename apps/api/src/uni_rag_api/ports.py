"""Domain-local ports for the API (L3).

These are API boundaries, not core contracts: Lane E's real retrieval service
will implement :class:`AnswerService` at integration. Ports stay synchronous;
adapters may be async internally (AGENT.md §4).
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from uni_rag_core import Answer, ObjectStore, PastPaperQuestion, Query
from uni_rag_indexing.domain.store_types import (
    PaperRecordFilters,
    ParsedPaperRecord,
)


@runtime_checkable
class AnswerService(Protocol):
    """Produces cited answers and their ordered text tokens."""

    def answer(self, query: Query) -> Answer:
        """Return a cited (or explicitly abstaining) answer for ``query``."""
        ...

    def tokens(self, answer: Answer) -> Iterator[str]:
        """Yield answer text tokens that join back to ``answer.text`` exactly."""
        ...


@runtime_checkable
class HealthProbe(Protocol):
    """Reports whether the injected dependencies are ready."""

    def is_ready(self) -> bool:
        """Return True when downstream dependencies are available."""
        ...


class PaperRecord(PastPaperQuestion):
    """A segmented paper question plus its source's frozen crawl time (L5).

    ``PastPaperQuestion`` stops at core ADR 0007's finder fields; ``last_crawled``
    is carried here so every returned record is traceable without a core change.
    """

    last_crawled: datetime


@dataclass(frozen=True)
class PaperFilters:
    """Typed finder filters and pagination; no settings or environment reads (L8)."""

    course_code: str | None = None
    year: int | None = None
    term: str | None = None
    exam_type: str | None = None
    department: str | None = None
    limit: int = 20
    offset: int = 0


@runtime_checkable
class PapersProvider(Protocol):
    """Finds past-paper records behind an API-local port (L3)."""

    def find(self, filters: PaperFilters) -> list[PaperRecord]:
        """Return stored records matching every supplied filter (AND, L4/L5)."""
        ...


@runtime_checkable
class PaperRecordStore(Protocol):
    """API-local view of Lane D's parsed-record store (ADR 0011, L3/L14).

    The domain-local methods stay in ``uni_rag_indexing``; this narrow Protocol
    is only what the API composes and injects. No core contract changes.
    """

    def upsert_paper_record(
        self, record: ParsedPaperRecord, *, ordinal: int, indexed_at: datetime
    ) -> None:
        """Persist a parsed record with its provenance frozen at write time."""
        ...

    def find_paper_records(self, filters: PaperRecordFilters) -> Sequence[ParsedPaperRecord]:
        """Return matching parsed records in stable ordinal order, then paginate."""
        ...


@runtime_checkable
class TypedObjectStore(ObjectStore, Protocol):
    """ObjectStore that can report a stored object's content type (ADR 0007)."""

    def content_type_of(self, key: str) -> str:
        """Return the content type recorded for ``key``."""
        ...


@dataclass(frozen=True)
class StoredImage:
    """Bytes and content type resolved from an object-store entry."""

    data: bytes
    content_type: str


@runtime_checkable
class ImageService(Protocol):
    """Synchronous image lookup used by the HTTP image route (L3)."""

    def get(self, ref_id: str) -> StoredImage:
        """Return stored bytes and their content type, or raise core NotFoundError."""
        ...


FakeCorpus = Mapping[str, Answer]
