"""Alembic baseline apply/revert and metadata-store behaviour on SQLite (L1/L12)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import OperationalError

from tests.factories import FIXED_TIME, chunk, document, question
from uni_rag_core import Chunk, FakeClock
from uni_rag_indexing.adapters.postgres_metadata_store import PostgresMetadataStore
from uni_rag_indexing.adapters.postgres_tables import (
    chunks,
    crawl_state,
    documents,
    metadata,
    parsed_paper_records,
)
from uni_rag_indexing.domain.metadata_memory import InMemoryMetadataStore
from uni_rag_indexing.domain.store_types import (
    ChunkRecord,
    CrawlState,
    PaperRecordFilters,
    ParsedPaperRecord,
    StorageConflictError,
    StorageConnectionError,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATIONS = REPO_ROOT / "infra" / "migrations"


def _config(engine: Engine) -> Config:
    cfg = Config(str(MIGRATIONS / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS))
    cfg.set_main_option("sqlalchemy.url", "sqlite://")
    cfg.attributes["engine"] = engine
    return cfg


def test_initial_migration_applies_and_reverts_cleanly(sqlite_engine: Engine) -> None:
    cfg = _config(sqlite_engine)
    command.upgrade(cfg, "head")
    inspector = inspect(sqlite_engine)
    assert {"documents", "chunks", "crawl_state", "parsed_paper_records"} <= set(
        inspector.get_table_names()
    )

    for table in (documents, chunks, crawl_state, parsed_paper_records):
        expected = set(table.columns.keys())
        actual = {column["name"] for column in inspector.get_columns(table.name)}
        assert actual == expected, f"schema drift in {table.name}"
    assert "deleted_at" in documents.columns and "deleted_at" in chunks.columns
    assert "version" in documents.columns and "version" in chunks.columns
    assert "last_crawled" in parsed_paper_records.columns

    command.downgrade(cfg, "base")
    assert not inspect(sqlite_engine).has_table("documents")
    assert not inspect(sqlite_engine).has_table("chunks")
    assert not inspect(sqlite_engine).has_table("crawl_state")
    assert not inspect(sqlite_engine).has_table("parsed_paper_records")


@pytest.fixture
def store(sqlite_engine: Engine, fixed_clock: FakeClock) -> PostgresMetadataStore:
    command.upgrade(_config(sqlite_engine), "head")
    return PostgresMetadataStore(sqlite_engine, clock=fixed_clock, host="postgres")


def test_document_round_trip_and_idempotent_upsert(store: PostgresMetadataStore) -> None:
    doc = document()
    store.upsert_document(doc, indexed_at=store._clock.now())
    store.upsert_document(doc, indexed_at=store._clock.now())
    restored = store.get_document(doc.doc_id)
    assert restored is not None and restored.content_hash == doc.content_hash
    assert restored.doc_type == doc.doc_type


def test_chunk_upsert_is_idempotent_and_soft_delete_retains_history(
    store: PostgresMetadataStore,
) -> None:
    doc = document()
    store.upsert_document(doc, indexed_at=store._clock.now())
    item: Chunk = chunk()
    stamp = store._clock.now()
    first = store.upsert_chunk(item, indexed_at=stamp)
    second = store.upsert_chunk(item, indexed_at=stamp)
    assert first == second
    assert len(store.list_chunk_history(item.doc_id)) == 1

    store.soft_delete_chunk(item.chunk_id, deleted_at=stamp, superseded_by="new-id")
    assert store.list_live_chunk_ids(item.doc_id) == ()
    history = store.list_chunk_history(item.doc_id)
    assert len(history) == 1 and isinstance(history[0], ChunkRecord)
    assert not history[0].is_live and history[0].superseded_by == "new-id"


def test_version_conflict_raises_typed_error(store: PostgresMetadataStore) -> None:
    store.upsert_document(document(), indexed_at=store._clock.now())
    store.upsert_chunk(chunk(), indexed_at=store._clock.now())
    changed = chunk().model_copy(update={"content_hash": "different"})
    with pytest.raises(StorageConflictError):
        store.upsert_chunk(changed, indexed_at=store._clock.now())


def test_crawl_state_round_trip(store: PostgresMetadataStore) -> None:
    state = CrawlState(
        doc_id="doc-1",
        last_crawled=store._clock.now(),
        content_hash="hash-doc-1",
        status="ok",
        attempts=1,
        error=None,
        updated_at=store._clock.now(),
    )
    store.upsert_crawl_state(state)
    assert store.get_crawl_state("doc-1") == state
    assert store.get_crawl_state("missing") is None


def test_connection_failure_carries_host_and_is_not_retried() -> None:
    class BrokenEngine:
        def connect(self) -> Any:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

        def begin(self) -> Any:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    store = PostgresMetadataStore(BrokenEngine(), host="postgres.example.edu")  # type: ignore[arg-type]
    with pytest.raises(StorageConnectionError) as exc:
        store.get_chunk("chunk-1")
    assert exc.value.context["host"] == "postgres.example.edu"


def test_parsed_paper_record_round_trip_and_immutable_provenance(
    store: PostgresMetadataStore,
) -> None:
    """ADR 0011: the stored record's frozen fields come back through find()."""
    record = ParsedPaperRecord.from_question(question(), last_crawled=FIXED_TIME)
    store.upsert_paper_record(record, ordinal=1, indexed_at=FIXED_TIME)
    store.upsert_paper_record(record, ordinal=1, indexed_at=FIXED_TIME)

    found = store.find_paper_records(PaperRecordFilters(course_code="CS-101", limit=5))
    assert found == (record,)
    assert found[0].source_url == record.source_url
    assert found[0].last_crawled == record.last_crawled
    assert found[0].page == record.page
    assert found[0].image_ref == record.image_ref

    changed = replace(record, source_url="https://example.edu/moved.pdf")
    with pytest.raises(StorageConflictError):
        store.upsert_paper_record(changed, ordinal=1, indexed_at=FIXED_TIME)


def test_parsed_paper_records_filter_and_paginate_in_ordinal_order(
    store: PostgresMetadataStore,
) -> None:
    """AND-combined filters and bounded pagination hold at the store boundary."""
    base = ParsedPaperRecord.from_question(question(), last_crawled=FIXED_TIME)
    for index, (course, year) in enumerate(((None, 2024), ("CS-101", 2023), ("CS-101", 2024))):
        store.upsert_paper_record(
            replace(base, question_id=f"q-{index}", course_code=course, year=year),
            ordinal=index,
            indexed_at=FIXED_TIME,
        )

    assert [item.question_id for item in store.find_paper_records(PaperRecordFilters())] == [
        "q-0",
        "q-1",
        "q-2",
    ]
    assert [
        item.question_id for item in store.find_paper_records(PaperRecordFilters(year=2024))
    ] == [
        "q-0",
        "q-2",
    ]
    assert [
        item.question_id
        for item in store.find_paper_records(PaperRecordFilters(year=2024, limit=1, offset=1))
    ] == ["q-2"]


def test_in_memory_paper_record_store_matches_the_relational_semantics(
    metadata_memory: InMemoryMetadataStore,
) -> None:
    """The fake used by the API's deterministic backend has the same contract."""
    base = ParsedPaperRecord.from_question(question(), last_crawled=FIXED_TIME)
    second = replace(base, question_id="q-2", course_code="MATH-101")
    metadata_memory.upsert_paper_record(base, ordinal=1, indexed_at=FIXED_TIME)
    metadata_memory.upsert_paper_record(second, ordinal=2, indexed_at=FIXED_TIME)

    assert metadata_memory.find_paper_records(PaperRecordFilters()) == (base, second)
    assert [
        item.question_id
        for item in metadata_memory.find_paper_records(PaperRecordFilters(course_code="CS-101"))
    ] == [base.question_id]
    with pytest.raises(StorageConflictError):
        metadata_memory.upsert_paper_record(
            replace(base, source_url="https://example.edu/moved.pdf"),
            ordinal=1,
            indexed_at=FIXED_TIME,
        )


def test_metadata_matches_alembic_tables() -> None:
    assert {table.name for table in metadata.tables.values()} == {
        "documents",
        "chunks",
        "crawl_state",
        "parsed_paper_records",
    }
