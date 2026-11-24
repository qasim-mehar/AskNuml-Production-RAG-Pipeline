"""Pure filter-translation and payload-derivation behaviour (L6/L9)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from uni_rag_core import Chunk, ValidationError
from uni_rag_indexing.domain.filters import (
    FILTERABLE_FIELDS,
    build_payload,
    derive_course_code,
    derive_department,
    derive_term,
    derive_year,
    matches_payload,
    next_version,
    point_id,
    soft_delete_payload,
    translate_filters,
)

L6_FIELDS = {
    "chunk_id",
    "doc_id",
    "source_url",
    "heading_path",
    "content_hash",
    "last_crawled",
    "doc_type",
    "version",
    "text",
    "page",
    "image_ref",
}


def test_payload_covers_mandatory_l6_fields_and_filter_columns(
    base_chunk: Chunk, fixed_time: datetime
) -> None:
    payload = build_payload(base_chunk, indexed_at=fixed_time)
    assert L6_FIELDS <= payload.keys()
    assert {
        "department",
        "course_code",
        "year",
        "term",
        "last_crawled_ts",
        "is_live",
    } <= payload.keys()
    assert payload["is_live"] is True
    assert payload["last_crawled"] == base_chunk.last_crawled.astimezone(UTC).isoformat()
    assert payload["image_ref"]["ref_id"] == base_chunk.image_ref.ref_id  # type: ignore[index]


def test_derived_filter_columns_are_deterministic(base_chunk: Chunk, fixed_time: datetime) -> None:
    payload = build_payload(base_chunk, indexed_at=fixed_time)
    assert payload["course_code"] == "CS-101"
    assert payload["department"] == "CS"
    assert payload["year"] == 2026
    assert payload["term"] == "midterm"
    assert payload == build_payload(base_chunk, indexed_at=fixed_time)


def test_filter_translation_returns_only_matching_payloads(
    base_chunk: Chunk, fixed_time: datetime
) -> None:
    payload = build_payload(base_chunk, indexed_at=fixed_time)
    spec = translate_filters(
        {
            "doc_type": "web_page",
            "department": "cs",
            "course_code": "cs-101",
            "year": "2026",
            "term": "midterm",
            "version": "1",
            "last_crawled_from": "2025-01-01T00:00:00+00:00",
            "last_crawled_to": "2027-01-01T00:00:00+00:00",
        }
    )
    assert matches_payload(payload, spec)
    assert not matches_payload(payload, translate_filters({"doc_type": "pdf"}))
    assert not matches_payload(payload, translate_filters({"year": "2025"}))
    assert not matches_payload(
        payload, translate_filters({"last_crawled_from": "2026-06-01T00:00:00+00:00"})
    )


def test_unknown_and_malformed_filters_raise_validation_error() -> None:
    with pytest.raises(ValidationError):
        translate_filters({"unmapped": "x"})
    with pytest.raises(ValidationError):
        translate_filters({"year": "not-a-year"})
    with pytest.raises(ValidationError):
        translate_filters({"doc_type": "novel"})
    with pytest.raises(ValidationError):
        translate_filters({"last_crawled_from": "yesterday"})


def test_soft_delete_preserves_payload_except_lifecycle_fields(
    base_chunk: Chunk, fixed_time: datetime
) -> None:
    payload = build_payload(base_chunk, indexed_at=fixed_time)
    stamp = datetime(2026, 1, 2, tzinfo=UTC)
    stale = soft_delete_payload(payload, deleted_at=stamp, superseded_by="new-id")
    assert stale["is_live"] is False
    assert stale["deleted_at"] == stamp.isoformat()
    assert stale["superseded_by"] == "new-id"
    assert stale["content_hash"] == payload["content_hash"]
    assert stale["text"] == payload["text"]
    assert payload["is_live"] is True  # original was not mutated


def test_ids_derive_from_content_hash_and_versions_bump(base_chunk: Chunk) -> None:
    assert point_id(base_chunk) == point_id(base_chunk)
    changed = base_chunk.model_copy(update={"version": "2", "content_hash": "other"})
    assert point_id(changed) != point_id(base_chunk)
    assert next_version("1", "1") == "2"
    assert next_version("1", "3") == "3"
    assert next_version("2", "1") == "3"
    assert next_version("v1", "v1") == "v1-2"
    assert next_version("v1-2", "v1") == "v1-3"  # repeated re-index never stalls
    assert next_version("v1", "v2") == "v2"


def test_derivation_helpers_are_pure(base_chunk: Chunk) -> None:
    assert derive_course_code(base_chunk) == "CS-101"
    assert derive_department(base_chunk) == "CS"
    assert derive_year(base_chunk) == 2026
    assert derive_term(base_chunk) == "midterm"
    assert FILTERABLE_FIELDS
