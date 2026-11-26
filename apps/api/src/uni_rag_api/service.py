"""Deterministic answer, parsed-record and object-store image services (L3, L4, L5).

Services own orchestration; routers only route and serialise (L9). No network
call happens here: the object store and the parsed-record store arrive as
injected synchronous ports (ADR 0011).
"""

from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime
from mimetypes import guess_type

from uni_rag_api.fixtures import CORPUS, FALLBACK_ANSWER
from uni_rag_api.ports import (
    AnswerService,
    FakeCorpus,
    HealthProbe,
    ImageService,
    PaperFilters,
    PaperRecord,
    PaperRecordStore,
    StoredImage,
    TypedObjectStore,
)
from uni_rag_core import Answer, NotFoundError, ObjectStore, PastPaperQuestion, Query, StorageError
from uni_rag_indexing.domain.store_types import PaperRecordFilters, ParsedPaperRecord


class FakeAnswerService:
    """Returns fixture answers, stamping only the request's ``query_id``.

    Citations, images and every provenance field are copied verbatim; the
    service never invents or strips them (L5, L6).
    """

    def __init__(self, corpus: FakeCorpus | None = None) -> None:
        self._corpus: Mapping[str, Answer] = dict(corpus if corpus is not None else CORPUS)

    def answer(self, query: Query) -> Answer:
        """Return the fixture answer for ``query.text``, or an abstaining fallback."""
        base = self._corpus.get(query.text.strip(), FALLBACK_ANSWER)
        return base.model_copy(update={"query_id": query.query_id})

    def tokens(self, answer: Answer) -> Iterator[str]:
        """Yield space-delimited tokens; ``" ".join(tokens) == answer.text``."""
        yield from answer.text.split(" ")


class StoredPapersProvider:
    """Real finder over Lane D's parsed-record store (ADR 0011, L3, L4, L5).

    No fixture lookup and no crawl happens at request time: the provider maps
    the API-local filters onto the domain-local store and rebuilds each record
    from the provenance frozen at write time. Storage errors propagate as typed
    ``StorageError`` subclasses for the app's 503 handler (L11).
    """

    def __init__(self, store: PaperRecordStore) -> None:
        self._store = store

    def find(self, filters: PaperFilters) -> list[PaperRecord]:
        """Return stored records matching every filter, in ordinal order."""
        domain_filters = PaperRecordFilters(
            course_code=filters.course_code,
            year=filters.year,
            term=filters.term,
            exam_type=filters.exam_type,
            department=filters.department,
            limit=filters.limit,
            offset=filters.offset,
        )
        return [
            _to_paper_record(record) for record in self._store.find_paper_records(domain_filters)
        ]


def _to_paper_record(record: ParsedPaperRecord) -> PaperRecord:
    """Rebuild an API record from a stored one; provenance is never recomputed."""
    return PaperRecord.model_validate(
        {**record.to_question().model_dump(mode="python"), "last_crawled": record.last_crawled}
    )


def seed_paper_records(
    store: PaperRecordStore,
    records: Sequence[PaperRecord],
    *,
    indexed_at: datetime,
) -> None:
    """Persist fixture-derived parsed records deterministically (fake mode only, ADR 0011).

    Live crawling and parsing stay parked; the real backend reads whatever the
    store already holds and is never seeded by this helper.
    """
    for ordinal, record in enumerate(records, start=1):
        stored = ParsedPaperRecord.from_question(
            PastPaperQuestion.model_validate(
                {
                    key: value
                    for key, value in record.model_dump(mode="python").items()
                    if key != "last_crawled"
                }
            ),
            last_crawled=record.last_crawled,
        )
        store.upsert_paper_record(stored, ordinal=ordinal, indexed_at=indexed_at)


class FakeHealthProbe:
    """Fake readiness signal, flippable in tests without touching real ports."""

    def __init__(self, ready: bool = True) -> None:
        self.ready = ready

    def is_ready(self) -> bool:
        """Return the configured readiness value."""
        return self.ready


class KeySuffixTypedStore:
    """Adapt a plain ObjectStore to TypedObjectStore with one deterministic rule."""

    def __init__(self, store: ObjectStore) -> None:
        self._store = store

    def put(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        """Store bytes through the wrapped port."""
        return self._store.put(key, data, content_type=content_type)

    def get(self, key: str) -> bytes:
        """Read bytes through the wrapped port."""
        return self._store.get(key)

    def delete(self, key: str) -> None:
        """Delete through the wrapped port."""
        self._store.delete(key)

    def content_type_of(self, key: str) -> str:
        """Derive the content type from the stored key's suffix."""
        guessed, _ = guess_type(key)
        return guessed or "application/octet-stream"


def as_typed_store(store: ObjectStore) -> TypedObjectStore:
    """Expose a uniform content-type lookup for fake and real stores (L4)."""
    return store if isinstance(store, TypedObjectStore) else KeySuffixTypedStore(store)


class ObjectStoreImageService:
    """Resolve ADR 0007 image refs through the frozen ObjectStore port (L3, L5)."""

    def __init__(self, store: TypedObjectStore) -> None:
        self._store = store

    def get(self, ref_id: str) -> StoredImage:
        """Return stored image bytes; missing keys raise a typed core NotFoundError."""
        if not ref_id or ref_id.startswith("/") or ".." in ref_id.split("/"):
            raise NotFoundError("Image reference does not exist.", context={"ref_id": ref_id})
        try:
            data = self._store.get(ref_id)
        except StorageError as exc:
            if not _is_missing(exc):
                raise
            raise NotFoundError(
                "Image reference does not exist.", context={"ref_id": ref_id}
            ) from exc
        return StoredImage(data=data, content_type=self._content_type(ref_id))

    def _content_type(self, ref_id: str) -> str:
        """Read the type from the store (recorded for fakes, key-derived for real)."""
        return self._store.content_type_of(ref_id)


def _is_missing(exc: StorageError) -> bool:
    """Distinguish a missing object (404) from a broken store (503)."""
    text = f"{type(exc).__name__}: {exc.message}".lower()
    return "not found" in text or "nosuchkey" in text or "404" in text


__all__ = [
    "AnswerService",
    "FakeAnswerService",
    "FakeHealthProbe",
    "HealthProbe",
    "ImageService",
    "KeySuffixTypedStore",
    "ObjectStoreImageService",
    "StoredPapersProvider",
    "as_typed_store",
    "seed_paper_records",
]
