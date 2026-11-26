"""SQLAlchemy metadata store for documents, chunk versions, crawl state and parsed records (L8/L10).

All connections come from the typed settings module; the engine is injected in
tests. Writes are idempotent by (chunk_id, version) and staleness is expressed
with ``deleted_at`` rather than row deletion. Parsed paper records are frozen
at write time (ADR 0011); they are never rebuilt from a crawl response on read.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, NoReturn

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, OperationalError

from uni_rag_core import (
    Chunk,
    Clock,
    DocType,
    Document,
    FakeClock,
    ImageRef,
    Language,
    Settings,
    StorageError,
    get_logger,
)
from uni_rag_indexing.adapters.postgres_tables import (
    chunks,
    crawl_state,
    documents,
    parsed_paper_records,
)
from uni_rag_indexing.domain.filters import build_payload, ensure_aware
from uni_rag_indexing.domain.store_types import (
    ChunkRecord,
    CrawlState,
    PaperRecordFilters,
    ParsedPaperRecord,
    StorageConflictError,
    StorageConnectionError,
)

_logger = get_logger("uni_rag_indexing.adapters.postgres")


class PostgresMetadataStore:
    """Domain-local MetadataStore implementation backed by SQLAlchemy Core."""

    def __init__(
        self, engine: Engine, *, clock: Clock | None = None, host: str = "postgres"
    ) -> None:
        self._engine = engine
        self._clock: Clock = clock or FakeClock()
        self._host = host

    @classmethod
    def from_settings(
        cls, settings: Settings, *, clock: Clock | None = None
    ) -> PostgresMetadataStore:
        """Build the engine from the single typed settings module (L8)."""
        url = make_url(settings.postgres_dsn)
        return cls(
            create_engine(settings.postgres_dsn, pool_pre_ping=True),
            clock=clock,
            host=url.host or "postgres",
        )

    # -- documents --------------------------------------------------------------
    def upsert_document(self, document: Document, *, indexed_at: datetime) -> None:
        """Insert a document or leave an identical one untouched."""
        ensure_aware(indexed_at, field="indexed_at")
        try:
            with self._engine.begin() as connection:
                row = connection.execute(
                    select(documents).where(documents.c.doc_id == document.doc_id)
                ).first()
                values = {
                    "source_url": document.source_url,
                    "title": document.title,
                    "doc_type": document.doc_type.value,
                    "last_crawled": ensure_aware(document.last_crawled, field="last_crawled"),
                    "content_hash": document.content_hash,
                    "version": document.version,
                    "language": document.language.value,
                    "metadata_json": dict(document.metadata),
                    "indexed_at": indexed_at,
                }
                if row is None:
                    connection.execute(
                        documents.insert().values(doc_id=document.doc_id, deleted_at=None, **values)
                    )
                elif row.content_hash != document.content_hash or row.version != document.version:
                    connection.execute(
                        documents.update()
                        .where(documents.c.doc_id == document.doc_id)
                        .values(**values)
                    )
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "upsert_document")
        _logger.info("postgres_document_upsert", doc_id=document.doc_id, host=self._host)

    def get_document(self, doc_id: str) -> Document | None:
        """Return the stored document or None."""
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    select(documents).where(documents.c.doc_id == doc_id)
                ).first()
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "get_document")
        if row is None:
            return None
        return Document(
            doc_id=row.doc_id,
            source_url=row.source_url,
            title=row.title,
            doc_type=DocType(row.doc_type),
            last_crawled=_aware(row.last_crawled),
            content_hash=row.content_hash,
            version=row.version,
            language=Language(row.language),
            metadata=dict(row.metadata_json or {}),
        )

    # -- chunks -----------------------------------------------------------------
    def get_chunk(self, chunk_id: str) -> ChunkRecord | None:
        """Return the newest chunk version, including soft-deleted rows."""
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    select(chunks)
                    .where(chunks.c.chunk_id == chunk_id)
                    .order_by(chunks.c.indexed_at.desc(), chunks.c.version.desc())
                    .limit(1)
                ).first()
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "get_chunk")
        return None if row is None else _to_record(row)

    def upsert_chunk(self, chunk: Chunk, *, indexed_at: datetime) -> ChunkRecord:
        """Insert a chunk version; identical writes are no-ops, conflicts raise."""
        ensure_aware(indexed_at, field="indexed_at")
        payload = build_payload(chunk, indexed_at=indexed_at)
        try:
            with self._engine.begin() as connection:
                row = connection.execute(
                    select(chunks).where(
                        chunks.c.chunk_id == chunk.chunk_id, chunks.c.version == chunk.version
                    )
                ).first()
                if row is not None:
                    if row.content_hash != chunk.content_hash:
                        raise StorageConflictError(
                            "chunk id/version already stored with different content",
                            context={"chunk_id": chunk.chunk_id, "version": chunk.version},
                        )
                    return _to_record(row)
                connection.execute(
                    chunks.insert().values(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        version=chunk.version,
                        content_hash=chunk.content_hash,
                        payload=payload,
                        indexed_at=indexed_at,
                        deleted_at=None,
                        superseded_by=None,
                    )
                )
        except StorageConflictError:
            raise
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "upsert_chunk")
        return ChunkRecord(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            version=chunk.version,
            content_hash=chunk.content_hash,
            payload=payload,
            indexed_at=ensure_aware(indexed_at, field="indexed_at"),
        )

    def soft_delete_chunk(
        self, chunk_id: str, *, deleted_at: datetime, superseded_by: str | None = None
    ) -> None:
        """Mark every live version stale; the row itself remains for history."""
        ensure_aware(deleted_at, field="deleted_at")
        try:
            with self._engine.begin() as connection:
                result = connection.execute(
                    chunks.update()
                    .where(chunks.c.chunk_id == chunk_id, chunks.c.deleted_at.is_(None))
                    .values(deleted_at=deleted_at, superseded_by=superseded_by)
                )
                if result.rowcount == 0:
                    _logger.debug("postgres_soft_delete_noop", chunk_id=chunk_id)
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "soft_delete_chunk")
        _logger.info("postgres_chunk_soft_delete", chunk_id=chunk_id, host=self._host)

    def list_live_chunk_ids(self, doc_id: str) -> Sequence[str]:
        """Return ids of live chunks for a document."""
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    select(chunks.c.chunk_id).where(
                        chunks.c.doc_id == doc_id, chunks.c.deleted_at.is_(None)
                    )
                ).all()
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "list_live_chunk_ids")
        return tuple(str(row.chunk_id) for row in rows)

    def list_chunk_history(self, doc_id: str) -> Sequence[ChunkRecord]:
        """Return all versions, soft-deleted included, for history tooling."""
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    select(chunks)
                    .where(chunks.c.doc_id == doc_id)
                    .order_by(chunks.c.chunk_id, chunks.c.version)
                ).all()
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "list_chunk_history")
        return tuple(_to_record(row) for row in rows)

    # -- crawl state ------------------------------------------------------------
    def upsert_crawl_state(self, state: CrawlState) -> None:
        """Persist the latest crawl outcome for a document."""
        values = {
            "last_crawled": ensure_aware(state.last_crawled, field="last_crawled"),
            "content_hash": state.content_hash,
            "status": state.status,
            "attempts": state.attempts,
            "error": state.error,
            "updated_at": ensure_aware(state.updated_at, field="updated_at"),
        }
        try:
            with self._engine.begin() as connection:
                row = connection.execute(
                    select(crawl_state.c.doc_id).where(crawl_state.c.doc_id == state.doc_id)
                ).first()
                if row is None:
                    connection.execute(crawl_state.insert().values(doc_id=state.doc_id, **values))
                else:
                    connection.execute(
                        crawl_state.update()
                        .where(crawl_state.c.doc_id == state.doc_id)
                        .values(**values)
                    )
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "upsert_crawl_state")
        _logger.info("postgres_crawl_state_upsert", doc_id=state.doc_id, status=state.status)

    def get_crawl_state(self, doc_id: str) -> CrawlState | None:
        """Return the stored crawl state or None."""
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    select(crawl_state).where(crawl_state.c.doc_id == doc_id)
                ).first()
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "get_crawl_state")
        if row is None:
            return None
        return CrawlState(
            doc_id=row.doc_id,
            last_crawled=_aware(row.last_crawled),
            content_hash=row.content_hash,
            status=row.status,
            attempts=int(row.attempts),
            error=row.error,
            updated_at=_aware(row.updated_at),
        )

    # -- parsed paper records (ADR 0011) ----------------------------------------
    def upsert_paper_record(
        self, record: ParsedPaperRecord, *, ordinal: int, indexed_at: datetime
    ) -> None:
        """Persist a parsed record; a replay with different provenance conflicts."""
        crawled = ensure_aware(record.last_crawled, field="last_crawled")
        stamped = ensure_aware(indexed_at, field="indexed_at")
        record_values = {
            "doc_id": record.doc_id,
            "source_url": record.source_url,
            "page": record.page,
            "question_number": record.question_number,
            "text": record.text,
            "last_crawled": crawled,
            "year": record.year,
            "subject": record.subject,
            "options_json": list(record.options),
            "image_ref_json": (
                None if record.image_ref is None else record.image_ref.model_dump(mode="json")
            ),
            "course_code": record.course_code,
            "term": record.term,
            "exam_type": record.exam_type,
            "department": record.department,
        }
        values = {**record_values, "ordinal": ordinal, "indexed_at": stamped}
        try:
            with self._engine.begin() as connection:
                row = connection.execute(
                    select(parsed_paper_records).where(
                        parsed_paper_records.c.question_id == record.question_id
                    )
                ).first()
                if row is None:
                    connection.execute(
                        parsed_paper_records.insert().values(
                            question_id=record.question_id, **values
                        )
                    )
                elif _paper_record_values(row) != record_values:
                    raise StorageConflictError(
                        "question_id already stored with a different parsed record",
                        context={"question_id": record.question_id},
                    )
        except StorageConflictError:
            raise
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "upsert_paper_record")
        _logger.info(
            "postgres_paper_record_upsert", question_id=record.question_id, host=self._host
        )

    def find_paper_records(self, filters: PaperRecordFilters) -> Sequence[ParsedPaperRecord]:
        """Return matching parsed records in stable ordinal order, then paginate."""
        query = select(parsed_paper_records)
        for column, value in (
            (parsed_paper_records.c.course_code, filters.course_code),
            (parsed_paper_records.c.year, filters.year),
            (parsed_paper_records.c.term, filters.term),
            (parsed_paper_records.c.exam_type, filters.exam_type),
            (parsed_paper_records.c.department, filters.department),
        ):
            if value is not None:
                query = query.where(column == value)
        query = (
            query.order_by(parsed_paper_records.c.ordinal, parsed_paper_records.c.question_id)
            .limit(filters.limit)
            .offset(filters.offset)
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query).all()
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "find_paper_records")
        return tuple(_to_paper_record(row) for row in rows)

    # -- internals --------------------------------------------------------------
    def _raise_typed(self, exc: Exception, operation: str) -> NoReturn:
        text = f"{type(exc).__name__}: {exc}".lower()
        context: dict[str, Any] = {"operation": operation, "host": self._host}
        _logger.error("postgres_error", operation=operation, host=self._host, error=text[:300])
        if isinstance(exc, IntegrityError) or "unique constraint" in text or "duplicate" in text:
            raise StorageConflictError(
                f"postgres conflict during {operation}: {exc}", context=context
            ) from exc
        if isinstance(exc, OperationalError) or any(
            token in text for token in ("connect", "refused", "unreachable", "timeout")
        ):
            raise StorageConnectionError(
                f"postgres connection failed during {operation}: {exc}", context=context
            ) from exc
        raise StorageError(f"postgres {operation} failed: {exc}", context=context) from exc


def _aware(value: datetime) -> datetime:
    """Normalise a DB datetime to UTC-aware form (SQLite drops tzinfo)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _utc_aware(value: datetime) -> datetime:
    """Convert a DB timestamp to UTC so JSON round-trips byte-faithfully (L5)."""
    return _aware(value).astimezone(UTC)


def _to_record(row: Any) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=row.chunk_id,
        doc_id=row.doc_id,
        version=row.version,
        content_hash=row.content_hash,
        payload=dict(row.payload or {}),
        indexed_at=_aware(row.indexed_at),
        deleted_at=None if row.deleted_at is None else _aware(row.deleted_at),
        superseded_by=row.superseded_by,
    )


def _paper_record_values(row: Any) -> dict[str, Any]:
    """Return the persisted columns of a parsed record in upsert-comparable form."""
    # ``ordinal`` and ``indexed_at`` are write-time bookkeeping, not part of the
    # frozen record: replaying the same record must remain a no-op (L4).
    return {
        "doc_id": row.doc_id,
        "source_url": row.source_url,
        "page": row.page,
        "question_number": row.question_number,
        "text": row.text,
        "last_crawled": _utc_aware(row.last_crawled),
        "year": row.year,
        "subject": row.subject,
        "options_json": list(row.options_json or ()),
        "image_ref_json": row.image_ref_json,
        "course_code": row.course_code,
        "term": row.term,
        "exam_type": row.exam_type,
        "department": row.department,
    }


def _to_paper_record(row: Any) -> ParsedPaperRecord:
    """Rebuild a parsed record from its frozen columns, never from a fetch."""
    return ParsedPaperRecord(
        question_id=row.question_id,
        doc_id=row.doc_id,
        source_url=row.source_url,
        page=row.page,
        question_number=row.question_number,
        text=row.text,
        last_crawled=_utc_aware(row.last_crawled),
        year=row.year,
        subject=row.subject,
        options=tuple(row.options_json or ()),
        image_ref=(
            None if row.image_ref_json is None else ImageRef.model_validate(row.image_ref_json)
        ),
        course_code=row.course_code,
        term=row.term,
        exam_type=row.exam_type,
        department=row.department,
    )


__all__ = ["PostgresMetadataStore"]
