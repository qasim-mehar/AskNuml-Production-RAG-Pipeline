"""Pure translation of chunk metadata into store-neutral filter specs (L6/L9).

No client, connection or I/O type appears in this module. Adapters map the
neutral dataclasses here onto their own query language; the in-memory index
uses the same predicates so fake mode and live mode agree on semantics.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from uni_rag_core import Chunk, DocType, ValidationError

COURSE_CODE_RE = re.compile(r"\b([A-Za-z]{2,6})[-\s]?(\d{3})\b")
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
TERM_WORDS = ("fall", "spring", "summer", "winter", "midterm", "final")

# Payload keys are shared by the Qdrant adapter, the Postgres payload column
# and the in-memory index. Renaming one here is a schema change (Alembic).
EQUALITY_FIELDS: frozenset[str] = frozenset(
    {
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
        "year",
        "page",
    }
)
RANGE_FIELDS: frozenset[str] = frozenset({"last_crawled_from", "last_crawled_to"})
FILTERABLE_FIELDS: frozenset[str] = EQUALITY_FIELDS | RANGE_FIELDS


@dataclass(frozen=True)
class Equals:
    """An exact match on one payload field."""

    field: str
    value: str | int | bool


@dataclass(frozen=True)
class Range:
    """An inclusive numeric range on one payload field."""

    field: str
    gte: float | None = None
    lte: float | None = None


@dataclass(frozen=True)
class FilterSpec:
    """A conjunction of neutral predicates, ordered deterministically."""

    must: tuple[Equals | Range, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Return True when no predicate is present."""
        return not self.must

    def with_live(self) -> FilterSpec:
        """Return a spec that additionally requires an undeleted payload."""
        return FilterSpec(must=self.must + live_only().must)


def live_only() -> FilterSpec:
    """Return the predicate every live query must apply (soft-delete rule)."""
    return FilterSpec(must=(Equals("is_live", True),))


def ensure_aware(value: datetime, *, field: str) -> datetime:
    """Return a UTC datetime, rejecting naive input (L4: no wall-clock reads)."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{field} must be timezone-aware", context={"field": field})
    return value.astimezone(UTC)


def iso_utc(value: datetime, *, field: str) -> str:
    """Render a timezone-aware datetime as a stable UTC ISO-8601 string."""
    return ensure_aware(value, field=field).isoformat()


def parse_iso(value: str, *, field: str) -> datetime:
    """Parse an ISO-8601 timestamp supplied by a caller."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field} is not a valid ISO-8601 timestamp", context={"field": field}
        ) from exc
    return ensure_aware(parsed, field=field)


def to_epoch(value: datetime | str, *, field: str) -> float:
    """Convert a timestamp to UTC epoch seconds for numeric range filters."""
    parsed = parse_iso(value, field=field) if isinstance(value, str) else value
    return ensure_aware(parsed, field=field).timestamp()


def derive_course_code(chunk: Chunk) -> str | None:
    """Extract a normalised course code (e.g. ``CS-101``) from L6 text fields."""
    for candidate in (*chunk.heading_path, chunk.source_url):
        match = COURSE_CODE_RE.search(candidate)
        if match is not None:
            return f"{match.group(1).upper()}-{match.group(2)}"
    return None


def derive_department(chunk: Chunk) -> str | None:
    """Extract the alphabetic department code from the derived course code."""
    code = derive_course_code(chunk)
    return code.split("-", 1)[0] if code else None


def derive_year(chunk: Chunk) -> int:
    """Use the first exam year in the L6 text, else the crawl year."""
    for candidate in (*chunk.heading_path, chunk.source_url):
        match = YEAR_RE.search(candidate)
        if match is not None:
            return int(match.group(1))
    return ensure_aware(chunk.last_crawled, field="last_crawled").year


def derive_term(chunk: Chunk) -> str | None:
    """Extract a controlled term keyword from the L6 heading path and URL."""
    haystack = " ".join((*chunk.heading_path, chunk.source_url)).lower()
    for word in TERM_WORDS:
        if re.search(rf"\b{word}\b", haystack):
            return word
    return None


def build_payload(chunk: Chunk, *, indexed_at: datetime) -> dict[str, Any]:
    """Build the complete, filterable payload for one chunk.

    Every L6 field is stored verbatim (or as an ISO string / JSON mapping) and
    the four derived columns make the mandatory filter axes pushdown-able.
    """
    stamp = iso_utc(indexed_at, field="indexed_at")
    crawled = ensure_aware(chunk.last_crawled, field="last_crawled")
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "source_url": chunk.source_url,
        "heading_path": list(chunk.heading_path),
        "content_hash": chunk.content_hash,
        "last_crawled": crawled.isoformat(),
        "last_crawled_ts": crawled.timestamp(),
        "doc_type": chunk.doc_type.value,
        "version": chunk.version,
        "text": chunk.text,
        "chunk_index": chunk.chunk_index,
        "token_count": chunk.token_count,
        "page": chunk.page,
        "image_ref": None if chunk.image_ref is None else chunk.image_ref.model_dump(mode="json"),
        "language": chunk.language.value,
        "department": derive_department(chunk),
        "course_code": derive_course_code(chunk),
        "year": derive_year(chunk),
        "term": derive_term(chunk),
        "is_live": True,
        "indexed_at": stamp,
        "deleted_at": None,
        "superseded_by": None,
    }


def soft_delete_payload(
    payload: Mapping[str, Any], *, deleted_at: datetime, superseded_by: str | None
) -> dict[str, Any]:
    """Return a copy of ``payload`` marked stale; the vector itself is kept."""
    updated = dict(payload)
    updated["is_live"] = False
    updated["deleted_at"] = iso_utc(deleted_at, field="deleted_at")
    updated["superseded_by"] = superseded_by
    return updated


def point_id(chunk: Chunk) -> str:
    """Return a deterministic id from the chunk identity and its content hash.

    Including ``chunk_id`` keeps two distinct chunks with identical text apart;
    including ``content_hash`` makes a replay of the same chunk idempotent and
    a content change produce a new versioned point.
    """
    return str(uuid5(NAMESPACE_URL, f"uni-rag:chunk:{chunk.chunk_id}:{chunk.content_hash}"))


def next_version(current: str, candidate: str) -> str:
    """Return a strictly greater version than ``current`` for a content change.

    Numeric versions increment; for labelled versions (``v1``) a ``-N`` suffix
    is advanced so repeated re-indexing never stalls on the same key. A newer
    candidate supplied by the caller wins; an older one cannot downgrade.
    """
    if current.isdigit() and candidate.isdigit():
        current_int, candidate_int = int(current), int(candidate)
        return str(candidate_int if candidate_int > current_int else current_int + 1)
    if candidate == current:
        return f"{candidate}-2"
    suffix = re.fullmatch(rf"{re.escape(candidate)}-(\d+)", current)
    if suffix is not None:
        return f"{candidate}-{int(suffix.group(1)) + 1}"
    if candidate > current:
        return candidate
    return f"{current}-2"


def translate_filters(filters: Mapping[str, str] | None) -> FilterSpec:
    """Validate and translate caller filters into a neutral conjunction.

    Unknown keys, malformed numbers and non-ISO timestamps raise
    :class:`ValidationError` instead of being silently ignored (L11).
    """
    if not filters:
        return FilterSpec()
    conditions: list[Equals | Range] = []
    for key, raw in filters.items():
        if key in RANGE_FIELDS:
            field = "last_crawled_ts"
            epoch = to_epoch(raw, field=key)
            conditions.append(
                Range(
                    field=field,
                    gte=epoch if key.endswith("_from") else None,
                    lte=epoch if key.endswith("_to") else None,
                )
            )
            continue
        if key not in EQUALITY_FIELDS:
            raise ValidationError(
                f"unsupported filter field: {key}",
                context={"field": key, "supported": sorted(FILTERABLE_FIELDS)},
            )
        value: str | int
        if key in {"year", "page"}:
            try:
                value = int(raw)
            except ValueError as exc:
                raise ValidationError(
                    f"{key} must be an integer", context={"field": key, "value": raw}
                ) from exc
        elif key == "doc_type":
            allowed = {item.value for item in DocType}
            if raw not in allowed:
                raise ValidationError(
                    f"unknown doc_type: {raw}", context={"field": key, "allowed": sorted(allowed)}
                )
            value = raw
        elif key in {"department", "course_code"}:
            value = raw.upper()
        elif key == "term":
            value = raw.lower()
        else:
            value = raw
        conditions.append(Equals(field=key, value=value))
    conditions.sort(key=lambda condition: (condition.field, str(condition)))
    return FilterSpec(must=tuple(conditions))


def matches_payload(payload: Mapping[str, Any], spec: FilterSpec) -> bool:
    """Return True when ``payload`` satisfies every predicate in ``spec``."""
    for condition in spec.must:
        actual = payload.get(condition.field)
        if isinstance(condition, Equals):
            if actual != condition.value:
                return False
        elif condition.gte is not None and (actual is None or float(actual) < condition.gte):
            return False
        elif condition.lte is not None and (actual is None or float(actual) > condition.lte):
            return False
    return True
