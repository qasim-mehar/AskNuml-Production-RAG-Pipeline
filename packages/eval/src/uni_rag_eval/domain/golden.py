"""Golden records, fixture corpus registry, and pure parsing/validation (L7, L12).

No file I/O and no wall-clock live here: callers supply parsed payloads and the
set of fixture paths that were verified to exist.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from datetime import datetime
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from uni_rag_core.errors import ValidationError as EvaluationValidationError
from uni_rag_core.schemas import Chunk, DocType, Language
from uni_rag_eval.domain.variant import (
    FIXED_WINDOW,
    INTEGRATED_CHUNKING,
    SENTENCE_BOUNDARY,
)

REQUIRED_LANGUAGES: tuple[Language, ...] = (
    Language.EN,
    Language.UR,
    Language.ROMAN_URDU,
)
# Latin and Urdu sentence terminators. Language-neutral, matching Lane C's
# sentence strategy, which honours both marks (L7).
_SENTENCE = re.compile(r"[^.!?۔؟]+[.!?۔؟]*", flags=re.UNICODE)


class GoldenRecord(BaseModel):
    """One curated question and the answer/retrieval facts the harness must check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    language: Language
    query: str
    expected_filters: dict[str, str] = Field(default_factory=dict)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_answer_gist: str
    expected_abstain: bool = False
    # Only feedback-derived rows carry a label. Curated rows leave it unset, so
    # the committed golden.json stays byte-identical and nothing is relabelled
    # as feedback after the fact (L1/L5).
    provenance: str | None = None


class GoldenSet(BaseModel):
    """A versioned, language-balanced collection of golden records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    golden_id: str
    description: str
    records: list[GoldenRecord]


class FixtureChunk(BaseModel):
    """A chunk definition grounded in one fixture document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    heading_path: list[str] = Field(default_factory=list)
    text: str
    # Real content hash from the integrated corpus (ADR 0007, L6). When present
    # it is validated against the chunk text, so a golden reference can never
    # silently point at a different chunk than the one the pipeline indexed.
    content_hash: str | None = None
    page: int | None = None
    language: Language = Language.EN


class FixtureDocument(BaseModel):
    """A fixture document and the chunk ids derived from it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str
    source_path: str
    source_url: str
    doc_type: DocType
    version: str
    last_crawled: str
    chunks: list[FixtureChunk]


class FixtureRegistry(BaseModel):
    """The curated fixture corpus, used as the fake backend's corpus."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    registry_id: str
    documents: list[FixtureDocument]


def load_golden_set(payload: Mapping[str, Any]) -> GoldenSet:
    """Parse a golden-set payload, raising a typed error on malformed input."""
    try:
        return GoldenSet.model_validate(dict(payload))
    except PydanticValidationError as exc:
        raise EvaluationValidationError(
            "Invalid golden set payload", context={"errors": exc.errors()}
        ) from exc


def load_fixture_registry(payload: Mapping[str, Any]) -> FixtureRegistry:
    """Parse a fixture registry payload, raising a typed error on malformed input."""
    try:
        return FixtureRegistry.model_validate(dict(payload))
    except PydanticValidationError as exc:
        raise EvaluationValidationError(
            "Invalid fixture registry payload", context={"errors": exc.errors()}
        ) from exc


def validate_golden_set(
    golden_set: GoldenSet,
    registry: FixtureRegistry,
    verified_source_paths: Collection[str],
) -> None:
    """Validate ids, abstention consistency, corpus references and L7 balance.

    Raises :class:`ValidationError` on the first invariant breach rather than
    skipping malformed records (L11/L13).
    """
    declared_paths = [doc.source_path for doc in registry.documents]
    missing_paths = sorted(set(declared_paths) - set(verified_source_paths))
    if missing_paths:
        raise EvaluationValidationError(
            "Fixture sources referenced by the registry do not exist",
            context={"missing_paths": missing_paths},
        )

    doc_ids = [doc.doc_id for doc in registry.documents]
    if len(doc_ids) != len(set(doc_ids)):
        raise EvaluationValidationError("Fixture registry has duplicate doc ids")
    chunk_ids = {chunk.chunk_id: doc.doc_id for doc in registry.documents for chunk in doc.chunks}
    if len(chunk_ids) != sum(len(doc.chunks) for doc in registry.documents):
        raise EvaluationValidationError("Fixture registry has duplicate chunk ids")

    seen: set[str] = set()
    counts: dict[Language, int] = {language: 0 for language in REQUIRED_LANGUAGES}
    for record in golden_set.records:
        if record.id in seen:
            raise EvaluationValidationError(
                "Duplicate golden record id", context={"record_id": record.id}
            )
        seen.add(record.id)
        if not record.query.strip() or not record.expected_answer_gist.strip():
            raise EvaluationValidationError(
                "Golden query and answer gist must be non-empty", context={"record_id": record.id}
            )
        if record.expected_abstain and record.expected_chunk_ids:
            raise EvaluationValidationError(
                "An abstain record cannot expect retrievable evidence",
                context={"record_id": record.id},
            )
        if not record.expected_abstain and not record.expected_chunk_ids:
            raise EvaluationValidationError(
                "An answerable record must name at least one expected chunk",
                context={"record_id": record.id},
            )
        expected_docs = {chunk_ids.get(chunk_id) for chunk_id in record.expected_chunk_ids}
        if None in expected_docs:
            unknown = sorted(
                chunk_id for chunk_id in record.expected_chunk_ids if chunk_id not in chunk_ids
            )
            raise EvaluationValidationError(
                "Golden record references a chunk outside the fixture corpus",
                context={"record_id": record.id, "unknown_chunk_ids": unknown},
            )
        filter_doc = record.expected_filters.get("doc_id")
        if filter_doc is not None and filter_doc not in expected_docs:
            raise EvaluationValidationError(
                "Golden filter doc_id disagrees with expected chunks",
                context={"record_id": record.id, "filter_doc_id": filter_doc},
            )
        counts[record.language] = counts.get(record.language, 0) + 1

    absent = sorted(language.value for language, count in counts.items() if count == 0)
    if absent:
        raise EvaluationValidationError(
            "Every supported language needs golden questions (L7)",
            context={"absent_languages": absent},
        )
    values = list(counts.values())
    if max(values) - min(values) > 1:
        raise EvaluationValidationError(
            "Golden set is not balanced across languages (L7)", context={"counts": counts}
        )


def chunks_from_registry(registry: FixtureRegistry) -> list[Chunk]:
    """Build core ``Chunk`` objects from the fixture registry (L6 fields included)."""
    chunks: list[Chunk] = []
    for doc in registry.documents:
        crawled = datetime.fromisoformat(doc.last_crawled)
        if crawled.tzinfo is None:
            raise EvaluationValidationError(
                "Fixture last_crawled must be timezone-aware",
                context={"doc_id": doc.doc_id, "last_crawled": doc.last_crawled},
            )
        for chunk in doc.chunks:
            computed_hash = sha256(chunk.text.encode("utf-8")).hexdigest()
            if chunk.content_hash is not None and chunk.content_hash != computed_hash:
                raise EvaluationValidationError(
                    "Fixture chunk content hash disagrees with its text",
                    context={"chunk_id": chunk.chunk_id, "declared": chunk.content_hash},
                )
            chunks.append(
                Chunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=doc.doc_id,
                    source_url=doc.source_url,
                    heading_path=list(chunk.heading_path),
                    content_hash=computed_hash,
                    last_crawled=crawled,
                    doc_type=doc.doc_type,
                    version=doc.version,
                    text=chunk.text,
                    language=chunk.language,
                    page=chunk.page,
                )
            )
    return chunks


def _sentences(text: str) -> tuple[str, ...]:
    """Split text on Latin and Urdu sentence marks, discarding empty fragments."""
    return tuple(part.strip() for part in _SENTENCE.findall(text) if part.strip())


def _require_strategy(strategy: str) -> str:
    if strategy not in (FIXED_WINDOW, SENTENCE_BOUNDARY):
        raise EvaluationValidationError(
            "Per-strategy corpora need one published chunking strategy",
            context={"strategy": strategy, "integrated": INTEGRATED_CHUNKING},
        )
    return strategy


def chunks_for_strategy(registry: FixtureRegistry, strategy: str) -> list[Chunk]:
    """Index the same fixture documents under one chunking strategy.

    ``fixed_window`` keeps the registry's hand-written chunk ids and text.
    ``sentence_boundary`` re-cuts every registry chunk at sentence marks and
    gives each sentence a derived id, so the two corpora have genuinely
    different chunk-id sets and different content hashes (L1/L4/L16). The
    provenance fields (doc id, source url, heading, crawl date, language, page)
    are carried over unchanged; only the boundaries and ids differ.
    """
    _require_strategy(strategy)
    if strategy == FIXED_WINDOW:
        return chunks_from_registry(registry)
    chunks: list[Chunk] = []
    for doc in registry.documents:
        crawled = datetime.fromisoformat(doc.last_crawled)
        if crawled.tzinfo is None:
            raise EvaluationValidationError(
                "Fixture last_crawled must be timezone-aware",
                context={"doc_id": doc.doc_id, "last_crawled": doc.last_crawled},
            )
        for chunk in doc.chunks:
            sentences = _sentences(chunk.text) or (chunk.text,)
            for index, sentence in enumerate(sentences):
                chunks.append(
                    Chunk(
                        chunk_id=f"{chunk.chunk_id}::sb{index:02d}",
                        doc_id=doc.doc_id,
                        source_url=doc.source_url,
                        heading_path=list(chunk.heading_path),
                        content_hash=sha256(sentence.encode("utf-8")).hexdigest(),
                        last_crawled=crawled,
                        doc_type=doc.doc_type,
                        version=doc.version,
                        text=sentence,
                        language=chunk.language,
                        page=chunk.page,
                    )
                )
    return chunks


def translate_expected_ids(
    registry: FixtureRegistry, chunk_ids: Sequence[str], strategy: str
) -> tuple[str, ...]:
    """Map registry chunk ids onto the ids actually indexed under ``strategy``.

    This keeps golden references resolvable in a per-strategy corpus rather
    than letting them dangle (L12). A missing id is an error, never a silent
    empty mapping.
    """
    _require_strategy(strategy)
    if strategy == FIXED_WINDOW:
        return tuple(chunk_ids)
    by_id = {chunk.chunk_id: chunk.text for doc in registry.documents for chunk in doc.chunks}
    translated: list[str] = []
    for chunk_id in chunk_ids:
        text = by_id.get(chunk_id)
        if text is None:
            raise EvaluationValidationError(
                "Golden record references a chunk outside the fixture corpus",
                context={"unknown_chunk_id": chunk_id},
            )
        sentences = _sentences(text) or (text,)
        translated.extend(f"{chunk_id}::sb{index:02d}" for index in range(len(sentences)))
    return tuple(translated)


def golden_for_strategy(
    golden_set: GoldenSet, registry: FixtureRegistry, strategy: str
) -> GoldenSet:
    """Return a golden set whose expected chunk ids exist in a strategy's corpus."""
    indexed_ids = {chunk.chunk_id for chunk in chunks_for_strategy(registry, strategy)}
    records: list[GoldenRecord] = []
    for record in golden_set.records:
        expected = list(translate_expected_ids(registry, record.expected_chunk_ids, strategy))
        dangling = sorted(set(expected) - indexed_ids)
        if dangling:
            raise EvaluationValidationError(
                "Per-strategy golden reference dangles against the indexed corpus",
                context={"record_id": record.id, "dangling_chunk_ids": dangling},
            )
        records.append(record.model_copy(update={"expected_chunk_ids": expected}))
    return golden_set.model_copy(update={"records": records})
