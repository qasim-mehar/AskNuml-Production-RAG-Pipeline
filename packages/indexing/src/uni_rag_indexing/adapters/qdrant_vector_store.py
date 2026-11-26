"""Qdrant implementation of the frozen VectorStore port (L3/L8/L10).

Dense and sparse collections are kept separate. Every live query adds an
``is_live`` predicate; superseded points stay in the collection for history
tooling but never appear in search results. Client creation is the only place
that reads settings; the rest of the adapter receives collaborators by
constructor injection (L4/L9).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn
from urllib.parse import urlsplit

from pydantic import ValidationError as PydanticValidationError
from qdrant_client import QdrantClient, models

from uni_rag_core import (
    Chunk,
    Clock,
    FakeClock,
    Settings,
    StorageError,
    VectorHit,
    get_logger,
)
from uni_rag_core import (
    ValidationError as CoreValidationError,
)
from uni_rag_indexing.domain.filters import (
    Equals,
    FilterSpec,
    Range,
    build_payload,
    point_id,
    soft_delete_payload,
    translate_filters,
)
from uni_rag_indexing.domain.store_types import (
    StorageConnectionError,
    StorageNotFoundError,
)

_logger = get_logger("uni_rag_indexing.adapters.qdrant")

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "sparse"

KEYWORD_FIELDS = (
    "chunk_id",
    "doc_id",
    "source_url",
    "doc_type",
    "language",
    "version",
    "content_hash",
    "department",
    "course_code",
    "term",
    "is_live",
)
INTEGER_FIELDS = ("year", "page", "chunk_index")
FLOAT_FIELDS = ("last_crawled_ts",)

# Storage-only filter predicates from ADR 0010. They stay in the Qdrant payload
# (and its indexes) but must never cross the VectorStore port in a VectorHit.
OPERATIONAL_FIELDS: frozenset[str] = frozenset(
    {
        "last_crawled_ts",
        "department",
        "course_code",
        "year",
        "term",
        "is_live",
        "indexed_at",
        "deleted_at",
        "superseded_by",
    }
)


def _host_from_url(url: str) -> str:
    """Return only the host (never credentials) for errors and log fields."""
    parsed = urlsplit(url)
    return parsed.hostname or url


def _stored_payload(chunk: Chunk, *, indexed_at: datetime) -> dict[str, Any]:
    """Build the filterable storage record: operational fields and metadata kept."""
    payload = build_payload(chunk, indexed_at=indexed_at)
    # build_payload normalises to UTC, which would lose the original offset on
    # the way back through the port; keep the exact timestamp for round-trips.
    payload["last_crawled"] = chunk.last_crawled.isoformat()
    payload["metadata"] = None if chunk.metadata is None else dict(chunk.metadata)
    return payload


def _domain_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the domain-clean ``Chunk`` dump allowed across the port (ADR 0010).

    Strips the operational fields before validation; re-dumping through ``Chunk``
    retains every declared field (including metadata) and canonicalises the JSON
    form. Because ``Chunk`` forbids extras, a strip that misses a storage field
    fails here instead of leaking into a retrieved hit. Malformed stored data is
    translated to the core typed error rather than leaking pydantic's exception.
    """
    clean = {key: value for key, value in payload.items() if key not in OPERATIONAL_FIELDS}
    try:
        return Chunk.model_validate(clean).model_dump(mode="json")
    except PydanticValidationError as exc:
        raise CoreValidationError(
            "malformed stored Qdrant payload is not a valid Chunk",
            context={"chunk_id": payload.get("chunk_id"), "errors": exc.errors()},
        ) from exc


def _to_hit(payload: Mapping[str, Any] | None, *, score: float) -> VectorHit:
    """Construct a port hit whose payload validates losslessly as a Chunk."""
    domain = _domain_payload(payload or {})
    return VectorHit(chunk_id=str(domain["chunk_id"]), score=float(score), payload=domain)


class QdrantVectorStore:
    """Synchronous VectorStore adapter with a Qdrant client behind the port."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        dimension: int = 16,
        dense_collection: str = "chunks_dense",
        sparse_collection: str = "chunks_sparse",
        clock: Clock | None = None,
        host: str = "qdrant",
        ensure: bool = True,
    ) -> None:
        self._client = client
        self._dimension = dimension
        self._dense = dense_collection
        self._sparse = sparse_collection
        self._clock: Clock = clock or FakeClock()
        self._host = host
        if ensure:
            self.ensure_collections()

    @classmethod
    def from_settings(cls, settings: Settings, *, clock: Clock | None = None) -> QdrantVectorStore:
        """Build a client from typed settings only; no ``os.environ`` reads (L8)."""
        client = QdrantClient(url=settings.qdrant_url, timeout=10)
        return cls(
            client,
            dimension=settings.embedding_dimension,
            clock=clock,
            host=_host_from_url(settings.qdrant_url),
        )

    # -- schema -----------------------------------------------------------------
    def ensure_collections(self) -> None:
        """Create dense/sparse collections and the filterable payload indexes."""
        try:
            if not self._client.collection_exists(self._dense):
                self._client.create_collection(
                    collection_name=self._dense,
                    vectors_config={
                        DENSE_VECTOR: models.VectorParams(
                            size=self._dimension, distance=models.Distance.COSINE
                        )
                    },
                )
            if not self._client.collection_exists(self._sparse):
                self._client.create_collection(
                    collection_name=self._sparse,
                    vectors_config={},
                    sparse_vectors_config={
                        SPARSE_VECTOR: models.SparseVectorParams(modifier=models.Modifier.IDF)
                    },
                )
            self._create_payload_indexes()
        except Exception as exc:  # translated below; never swallowed (L11)
            self._raise_typed(exc, "ensure_collections")
        _logger.info(
            "qdrant_collections_ready",
            dense=self._dense,
            sparse=self._sparse,
            dimension=self._dimension,
            host=self._host,
        )

    def _create_payload_indexes(self) -> None:
        schemas: tuple[tuple[tuple[str, ...], Any], ...] = (
            (KEYWORD_FIELDS, models.PayloadSchemaType.KEYWORD),
            (INTEGER_FIELDS, models.PayloadSchemaType.INTEGER),
            (FLOAT_FIELDS, models.PayloadSchemaType.FLOAT),
        )
        for fields, schema in schemas:
            for field in fields:
                try:
                    self._client.create_payload_index(
                        collection_name=self._dense, field_name=field, field_schema=schema
                    )
                except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
                    if "already exist" not in str(exc).lower():
                        self._raise_typed(exc, "create_payload_index")
                try:
                    self._client.create_payload_index(
                        collection_name=self._sparse, field_name=field, field_schema=schema
                    )
                except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
                    if "already exist" not in str(exc).lower():
                        self._raise_typed(exc, "create_payload_index")
        _logger.debug("qdrant_payload_indexes_ready", host=self._host)

    # -- VectorStore port -------------------------------------------------------
    def upsert(self, items: Sequence[tuple[Chunk, Sequence[float]]]) -> None:
        """Insert or replace chunk/vector pairs without changing identical data."""
        try:
            for chunk, vector in items:
                pid = point_id(chunk)
                existing = self._client.retrieve(
                    collection_name=self._dense, ids=[pid], with_payload=True
                )
                if existing and self._same(existing[0].payload, chunk):
                    _logger.debug("qdrant_upsert_skipped", chunk_id=chunk.chunk_id, host=self._host)
                    continue
                stamp = self._clock.now()
                self._soften_live(
                    chunk.chunk_id,
                    superseded_by=pid,
                    deleted_at=stamp,
                    keep_content_hash=chunk.content_hash,
                )
                payload = _stored_payload(chunk, indexed_at=stamp)
                self._client.upsert(
                    collection_name=self._dense,
                    points=[
                        models.PointStruct(
                            id=pid,
                            vector={DENSE_VECTOR: [float(value) for value in vector]},
                            payload=payload,
                        )
                    ],
                )
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "upsert")
        _logger.info("qdrant_upsert", count=len(items), host=self._host)

    def search(
        self,
        vector: Sequence[float],
        *,
        top_k: int,
        filters: Mapping[str, str] | None = None,
    ) -> list[VectorHit]:
        """Return live hits ordered by descending cosine similarity."""
        if top_k <= 0:
            return []
        query_filter = _to_qdrant(translate_filters(filters).with_live())
        try:
            response = self._client.query_points(
                collection_name=self._dense,
                query=[float(value) for value in vector],
                using=DENSE_VECTOR,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "search")
        hits = [_to_hit(point.payload, score=point.score) for point in response.points]
        _logger.debug("qdrant_search", top_k=top_k, hits=len(hits), host=self._host)
        return hits

    def delete(self, doc_id: str) -> None:
        """Soft-delete every live vector of a document; vectors are retained."""
        try:
            self._soften_by_field("doc_id", doc_id, deleted_at=self._clock.now())
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "delete")
        _logger.info("qdrant_soft_delete", doc_id=doc_id, host=self._host)

    # -- Optional capabilities (domain-local, not a core port change) ----------
    def mark_stale(self, chunk_id: str, *, superseded_by: str, deleted_at: Any) -> None:
        """Soft-delete live vectors for a superseded chunk id."""
        try:
            self._soften_live(chunk_id, superseded_by=superseded_by, deleted_at=deleted_at)
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "mark_stale")
        _logger.info("qdrant_mark_stale", chunk_id=chunk_id, host=self._host)

    def is_present(self, chunk_id: str) -> bool:
        """Return True when a live point exists for a chunk id."""
        spec = FilterSpec(must=(Equals("chunk_id", chunk_id), Equals("is_live", True)))
        try:
            count = self._client.count(
                collection_name=self._dense, count_filter=_to_qdrant(spec), exact=True
            ).count
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "is_present")
        return count > 0

    def upsert_sparse(
        self,
        chunk: Chunk,
        *,
        indices: Sequence[int],
        values: Sequence[float],
    ) -> str:
        """Insert a sparse vector into the sparse collection; return the point id."""
        pid = point_id(chunk)
        try:
            stamp = self._clock.now()
            self._soften_live(
                chunk.chunk_id,
                superseded_by=pid,
                deleted_at=stamp,
                collections=(self._sparse,),
                keep_content_hash=chunk.content_hash,
            )
            payload = _stored_payload(chunk, indexed_at=stamp)
            self._client.upsert(
                collection_name=self._sparse,
                points=[
                    models.PointStruct(
                        id=pid,
                        vector={
                            SPARSE_VECTOR: models.SparseVector(
                                indices=list(indices), values=[float(v) for v in values]
                            )
                        },
                        payload=payload,
                    )
                ],
            )
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "upsert_sparse")
        return pid

    def search_sparse(
        self,
        *,
        indices: Sequence[int],
        values: Sequence[float],
        top_k: int,
        filters: Mapping[str, str] | None = None,
    ) -> list[VectorHit]:
        """Return live sparse hits; uses the same translated filters as dense search."""
        if top_k <= 0:
            return []
        sparse = models.SparseVector(indices=list(indices), values=[float(v) for v in values])
        query_filter = _to_qdrant(translate_filters(filters).with_live())
        try:
            response = self._client.query_points(
                collection_name=self._sparse,
                query=sparse,
                using=SPARSE_VECTOR,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:  # noqa: BLE001 - classified, re-raised typed
            self._raise_typed(exc, "search_sparse")
        return [_to_hit(point.payload, score=point.score) for point in response.points]

    # -- internals --------------------------------------------------------------
    def _soften_live(
        self,
        chunk_id: str,
        *,
        superseded_by: str,
        deleted_at: Any,
        collections: Sequence[str] | None = None,
        keep_content_hash: str | None = None,
    ) -> None:
        self._soften_by_field(
            "chunk_id",
            chunk_id,
            deleted_at=deleted_at,
            superseded_by=superseded_by,
            collections=collections,
            keep_content_hash=keep_content_hash,
        )

    def _soften_by_field(
        self,
        field: str,
        value: str,
        *,
        deleted_at: Any,
        superseded_by: str | None = None,
        collections: Sequence[str] | None = None,
        keep_content_hash: str | None = None,
    ) -> None:
        """Soft-delete matching live points in *both* collections.

        Dense and sparse points share the payload schema, so a superseded chunk
        must be retired in each collection or a sparse query would still expose
        stale evidence.
        """
        selector = models.Filter(
            must=[
                models.FieldCondition(key=field, match=models.MatchValue(value=value)),
                models.FieldCondition(key="is_live", match=models.MatchValue(value=True)),
            ]
        )
        for collection in collections if collections is not None else (self._dense, self._sparse):
            offset = None
            while True:
                points, offset = self._client.scroll(
                    collection_name=collection,
                    scroll_filter=selector,
                    limit=128,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for point in points:
                    current = point.payload or {}
                    if (
                        keep_content_hash is not None
                        and current.get("content_hash") == keep_content_hash
                    ):
                        continue
                    payload = soft_delete_payload(
                        current, deleted_at=deleted_at, superseded_by=superseded_by
                    )
                    self._client.set_payload(
                        collection_name=collection, payload=payload, points=[point.id]
                    )
                if offset is None or not points:
                    break

    @staticmethod
    def _same(payload: Mapping[str, Any] | None, chunk: Chunk) -> bool:
        if payload is None:
            return False
        metadata = None if chunk.metadata is None else dict(chunk.metadata)
        return (
            payload.get("content_hash") == chunk.content_hash
            and payload.get("version") == chunk.version
            and payload.get("is_live") is True
            and payload.get("metadata") == metadata
        )

    def _raise_typed(self, exc: Exception, operation: str) -> NoReturn:
        text = f"{type(exc).__name__}: {exc}".lower()
        base = {"operation": operation, "host": self._host}
        _logger.error("qdrant_error", operation=operation, host=self._host, error=text[:300])
        if any(
            token in text
            for token in ("connect", "refused", "unavailable", "timeout", "unreachable")
        ):
            raise StorageConnectionError(
                f"qdrant connection failed during {operation}: {exc}", context=base
            ) from exc
        if any(token in text for token in ("not found", "404", "does not exist")):
            raise StorageNotFoundError(
                f"qdrant resource missing during {operation}: {exc}", context=base
            ) from exc
        raise StorageError(f"qdrant {operation} failed: {exc}", context=base) from exc


def _to_qdrant(spec: FilterSpec) -> models.Filter:
    """Map a neutral FilterSpec onto Qdrant's filter model."""
    must: list[models.FieldCondition] = []
    for condition in spec.must:
        if isinstance(condition, Equals):
            must.append(
                models.FieldCondition(
                    key=condition.field, match=models.MatchValue(value=condition.value)
                )
            )
        elif isinstance(condition, Range):
            must.append(
                models.FieldCondition(
                    key=condition.field,
                    range=models.Range(gte=condition.gte, lte=condition.lte),
                )
            )
    return models.Filter(must=must)
