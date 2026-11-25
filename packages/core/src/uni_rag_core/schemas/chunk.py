"""Retrieval unit contracts, including the mandatory L6 metadata fields."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from uni_rag_core.schemas.enums import DocType, Language

PayloadValue = str | int | float | bool | None | list[str]


class ImageRef(BaseModel):
    """A reference to a stored page/screenshot image (object-store key)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ref_id: str
    source_url: str
    page: int | None = None
    caption: str | None = None
    mime_type: str = "image/png"
    image_url: str | None = None


class Chunk(BaseModel):
    """A chunk with full provenance. Fields marked required are frozen by L6."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    doc_id: str
    source_url: str
    heading_path: list[str]
    content_hash: str
    last_crawled: datetime
    doc_type: DocType
    version: str
    text: str
    chunk_index: int = 0
    token_count: int | None = None
    page: int | None = None
    image_ref: ImageRef | None = None
    language: Language = Language.EN
    metadata: Mapping[str, str] | None = None


class ScoredChunk(BaseModel):
    """A chunk with a reranker score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk: Chunk
    score: float
    rank: int = 0


class VectorHit(BaseModel):
    """A vector-store search result.

    ``payload`` is the domain ``Chunk`` dump returned across the ``VectorStore``
    port: it validates losslessly as ``Chunk`` (ADR 0010). Storage-only fields
    may exist in the adapter's record but must not cross this boundary.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)
