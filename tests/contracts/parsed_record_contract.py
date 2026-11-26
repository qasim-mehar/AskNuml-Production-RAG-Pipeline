"""Executable ADR 0011 contract for the parsed-record store and papers provider.

Every store that claims to back ``GET /api/v1/papers`` must round-trip a stored
``PaperRecord`` through ``find()`` with its frozen provenance intact. The helper
is reused by the Postgres adapter contract test and the API lane.
"""

from datetime import timedelta

from uni_rag_api.ports import PaperFilters, PaperRecord, PaperRecordStore
from uni_rag_api.service import StoredPapersProvider, seed_paper_records
from uni_rag_core import ObjectStore


def assert_parsed_record_roundtrip_contract(
    store: PaperRecordStore, record: PaperRecord, *, object_store: ObjectStore
) -> None:
    """A persisted record returns through find() with provenance byte-faithful.

    ``source_url``, ``last_crawled``, ``page`` and the image reference are frozen
    at write time: the provider rebuilds the record from storage and never
    re-fetches or reconstructs them (L5, ADR 0011).
    """
    # A distinct storage timestamp keeps ``indexed_at`` distinguishable from
    # the frozen ``last_crawled`` the contract is proving.
    seed_paper_records(store, (record,), indexed_at=record.last_crawled + timedelta(days=1))

    provider = StoredPapersProvider(store)
    found = provider.find(PaperFilters(course_code=record.course_code, limit=20))

    assert found == [record]
    assert found[0].source_url == record.source_url
    assert found[0].last_crawled == record.last_crawled
    assert found[0].page == record.page
    assert found[0].image_ref == record.image_ref
    if found[0].image_ref is not None:
        assert object_store.get(found[0].image_ref.ref_id)
