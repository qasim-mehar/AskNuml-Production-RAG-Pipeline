"""Deterministic fake answer and object-store-backed image services (L3, L4, L5).

Services own orchestration; routers only route and serialise (L9). No network
call happens here: the object store arrives as an injected synchronous port.
"""

from collections.abc import Iterator, Mapping, Sequence
from mimetypes import guess_type

from uni_rag_api.fixtures import CORPUS, FALLBACK_ANSWER, PAPER_RECORDS
from uni_rag_api.ports import (
    AnswerService,
    FakeCorpus,
    HealthProbe,
    ImageService,
    PaperFilters,
    PaperRecord,
    StoredImage,
    TypedObjectStore,
)
from uni_rag_core import Answer, NotFoundError, ObjectStore, Query, StorageError


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


class FakePapersProvider:
    """Deterministic fixture-backed finder; no store or network (L3, L4)."""

    def __init__(self, records: Sequence[PaperRecord] | None = None) -> None:
        self._records: tuple[PaperRecord, ...] = tuple(
            records if records is not None else PAPER_RECORDS
        )

    def find(self, filters: PaperFilters) -> list[PaperRecord]:
        """Return records matching every filter, in fixture order, then paginate."""
        matched = [record for record in self._records if _matches_paper_filters(record, filters)]
        return matched[filters.offset : filters.offset + filters.limit]


def _matches_paper_filters(record: PaperRecord, filters: PaperFilters) -> bool:
    """AND every supplied filter; a None filter is no constraint (L4)."""
    return (
        (filters.course_code is None or record.course_code == filters.course_code)
        and (filters.year is None or record.year == filters.year)
        and (filters.term is None or record.term == filters.term)
        and (filters.exam_type is None or record.exam_type == filters.exam_type)
        and (filters.department is None or record.department == filters.department)
    )


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
    "FakePapersProvider",
    "HealthProbe",
    "ImageService",
    "KeySuffixTypedStore",
    "ObjectStoreImageService",
    "as_typed_store",
]
