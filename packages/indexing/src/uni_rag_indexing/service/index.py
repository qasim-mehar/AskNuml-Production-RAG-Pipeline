"""Indexing orchestration: embed, upsert, verify, soft-delete stale versions (L4/L9).

The service depends only on ports and domain-local Protocols, never on a
concrete Qdrant/MinIO/Postgres client. All timestamps come from the injected
Clock, so replaying the same corpus produces no observable write.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from uni_rag_core import (
    Chunk,
    Clock,
    Embedder,
    ImageRef,
    ObjectStore,
    StorageError,
    VectorStore,
    get_logger,
)
from uni_rag_indexing.domain.filters import next_version, point_id
from uni_rag_indexing.domain.store_types import (
    ChunkRecord,
    IndexResult,
    MetadataStore,
    VersionedVectorStore,
)

_logger = get_logger("uni_rag_indexing.service.index")


class IndexingService:
    """Drive a batch of chunks through embedding, storage and verification."""

    def __init__(
        self,
        *,
        vectors: VectorStore,
        objects: ObjectStore,
        metadata: MetadataStore,
        embedder: Embedder,
        clock: Clock,
    ) -> None:
        self._vectors = vectors
        self._objects = objects
        self._metadata = metadata
        self._embedder = embedder
        self._clock = clock

    def index(self, chunks: Sequence[Chunk]) -> IndexResult:
        """Index every chunk, skipping identical data and retiring stale versions."""
        result = IndexResult()
        for chunk in chunks:
            existing = self._metadata.get_chunk(chunk.chunk_id)
            if existing is not None and self._unchanged(existing, chunk):
                result = replace(result, unchanged=result.unchanged + 1)
                _logger.debug("index_skipped_identical", chunk_id=chunk.chunk_id)
                continue

            version = (
                next_version(existing.version, chunk.version)
                if existing is not None
                else chunk.version
            )
            new_chunk = (
                chunk if version == chunk.version else chunk.model_copy(update={"version": version})
            )
            stamp = self._clock.now()
            vector = self._embedder.embed([new_chunk.text])[0]
            # Retire the old version *before* inserting the new point: mark_stale
            # targets every live point for the chunk id, and the new one must not
            # exist yet or it would be retired in the same pass.
            if existing is not None:
                superseded = point_id(new_chunk)
                if isinstance(self._vectors, VersionedVectorStore):
                    self._vectors.mark_stale(
                        existing.chunk_id, superseded_by=superseded, deleted_at=stamp
                    )
                self._metadata.soft_delete_chunk(
                    existing.chunk_id, deleted_at=stamp, superseded_by=superseded
                )
                result = replace(
                    result,
                    updated=result.updated + 1,
                    stale_soft_deleted=result.stale_soft_deleted + 1,
                )

            self._vectors.upsert([(new_chunk, vector)])
            record = self._metadata.upsert_chunk(new_chunk, indexed_at=stamp)
            self._verify(new_chunk, vector)
            result = replace(
                result,
                inserted=result.inserted + (1 if existing is None else 0),
                verified=result.verified + 1,
            )
            _logger.info(
                "index_chunk",
                chunk_id=new_chunk.chunk_id,
                doc_id=new_chunk.doc_id,
                version=record.version,
            )
        _logger.info("index_batch_complete", total=result.total, verified=result.verified)
        return result

    def index_page_image(self, image_ref: ImageRef, data: bytes) -> str:
        """Store page-image bytes and return the content-addressed object key."""
        key = self._objects.put(image_ref.ref_id, data, content_type=image_ref.mime_type)
        _logger.info("page_image_stored", ref_id=image_ref.ref_id, key=key)
        return key

    def reindex_document(self, doc_id: str, chunks: Sequence[Chunk]) -> IndexResult:
        """Index a fresh corpus and soft-delete chunks that disappeared from it."""
        result = self.index(chunks)
        keep = {chunk.chunk_id for chunk in chunks}
        stamp = self._clock.now()
        for stale_id in self._metadata.list_live_chunk_ids(doc_id):
            if stale_id in keep:
                continue
            self._metadata.soft_delete_chunk(stale_id, deleted_at=stamp, superseded_by=None)
            if isinstance(self._vectors, VersionedVectorStore):
                self._vectors.mark_stale(stale_id, superseded_by="", deleted_at=stamp)
        _logger.info("reindex_document_complete", doc_id=doc_id, chunks=len(chunks))
        return result

    @staticmethod
    def _unchanged(record: ChunkRecord, chunk: Chunk) -> bool:
        return (
            record.content_hash == chunk.content_hash
            and record.version == chunk.version
            and record.is_live
        )

    def _verify(self, chunk: Chunk, vector: Sequence[float]) -> None:
        """Confirm the chunk is queryable after the upsert; fail loudly otherwise."""
        if isinstance(self._vectors, VersionedVectorStore):
            present = self._vectors.is_present(chunk.chunk_id)
        else:
            hits = self._vectors.search(
                vector, top_k=1, filters={"doc_id": chunk.doc_id, "version": chunk.version}
            )
            present = any(hit.chunk_id == chunk.chunk_id for hit in hits)
        if not present:
            _logger.error("index_verify_failed", chunk_id=chunk.chunk_id)
            raise StorageError(
                f"chunk not queryable after upsert: {chunk.chunk_id}",
                context={"chunk_id": chunk.chunk_id},
            )
        _logger.debug("index_verified", chunk_id=chunk.chunk_id)
