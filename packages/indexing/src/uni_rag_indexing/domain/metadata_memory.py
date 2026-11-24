"""Deterministic in-memory MetadataStore fake used by service tests (L4/L12)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from uni_rag_core import Chunk, Document
from uni_rag_indexing.domain.filters import build_payload, ensure_aware
from uni_rag_indexing.domain.store_types import (
    ChunkRecord,
    CrawlState,
    StorageConflictError,
)


class InMemoryMetadataStore:
    """Stores every chunk version and supports soft-delete without row removal."""

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._chunks: dict[tuple[str, str], ChunkRecord] = {}
        self._crawl: dict[str, CrawlState] = {}

    def upsert_document(self, document: Document, *, indexed_at: datetime) -> None:
        """Store a document, ignoring a byte-identical replay."""
        self._documents[document.doc_id] = document

    def get_document(self, doc_id: str) -> Document | None:
        """Return a stored document or None."""
        return self._documents.get(doc_id)

    def get_chunk(self, chunk_id: str) -> ChunkRecord | None:
        """Return the most recently indexed version for a chunk id."""
        matches = [record for (cid, _), record in self._chunks.items() if cid == chunk_id]
        if not matches:
            return None
        # A replay uses the same injected timestamp; prefer the live version so
        # "current" never regresses to a soft-deleted one.
        return max(
            matches,
            key=lambda item: (item.is_live, item.indexed_at, item.version),
        )

    def upsert_chunk(self, chunk: Chunk, *, indexed_at: datetime) -> ChunkRecord:
        """Insert a version; identical replays are no-ops, conflicts raise."""
        key = (chunk.chunk_id, chunk.version)
        existing = self._chunks.get(key)
        if existing is not None:
            if existing.content_hash != chunk.content_hash:
                raise StorageConflictError(
                    "chunk id/version already stored with different content",
                    context={"chunk_id": chunk.chunk_id, "version": chunk.version},
                )
            return existing
        record = ChunkRecord(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            version=chunk.version,
            content_hash=chunk.content_hash,
            payload=build_payload(chunk, indexed_at=ensure_aware(indexed_at, field="indexed_at")),
            indexed_at=ensure_aware(indexed_at, field="indexed_at"),
        )
        self._chunks[key] = record
        return record

    def soft_delete_chunk(
        self, chunk_id: str, *, deleted_at: datetime, superseded_by: str | None = None
    ) -> None:
        """Mark all live versions stale; rows remain for history tooling."""
        stamp = ensure_aware(deleted_at, field="deleted_at")
        for key, record in list(self._chunks.items()):
            if key[0] == chunk_id and record.deleted_at is None:
                self._chunks[key] = replace(record, deleted_at=stamp, superseded_by=superseded_by)

    def list_live_chunk_ids(self, doc_id: str) -> Sequence[str]:
        """Return live chunk ids for a document."""
        return tuple(
            cid
            for (cid, _), record in self._chunks.items()
            if record.doc_id == doc_id and record.is_live
        )

    def list_chunk_history(self, doc_id: str) -> Sequence[ChunkRecord]:
        """Return every stored version for a document, including stale rows."""
        return tuple(
            sorted(
                (record for record in self._chunks.values() if record.doc_id == doc_id),
                key=lambda item: (item.chunk_id, item.version),
            )
        )

    def upsert_crawl_state(self, state: CrawlState) -> None:
        """Store the latest crawl outcome."""
        self._crawl[state.doc_id] = state

    def get_crawl_state(self, doc_id: str) -> CrawlState | None:
        """Return a stored crawl outcome or None."""
        return self._crawl.get(doc_id)

    def history_count(self) -> int:
        """Return the number of retained versions (fake-specific helper)."""
        return len(self._chunks)
