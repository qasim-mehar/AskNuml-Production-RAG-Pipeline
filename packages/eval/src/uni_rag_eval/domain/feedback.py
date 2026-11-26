"""Offline feedback-to-golden ingestion from a labelled fixture transcript (L1/L5/L7/L12).

H2's ``POST /api/v1/feedback`` route is live but persists nothing (ADR 0009), so
there is no real feedback stream to ingest. This module deliberately accepts only
a fixture-shaped transcript whose ``live_feedback`` flag is false and stamps every
derived golden row with an explicit provenance label. No backend label may claim
live feedback; real feedback-to-golden ingestion stays parked until a storage ADR.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from uni_rag_core.errors import ValidationError
from uni_rag_core.schemas import Language
from uni_rag_eval.domain.golden import (
    REQUIRED_LANGUAGES,
    FixtureRegistry,
    GoldenRecord,
    GoldenSet,
)

FEEDBACK_SOURCE = "fixture-transcript"
FEEDBACK_PROVENANCE = f"feedback-derived|source={FEEDBACK_SOURCE}|live_feedback=False"
# The backend-label marker is the single token report renderers and the label
# guard key on, so a golden row and a table can never disagree about the source.
FEEDBACK_BACKEND_MARKER = f"feedback_source={FEEDBACK_SOURCE}"
# Substrings that would let a label imply a live feedback stream. The provider
# flag ``live=False`` is about retrieval transports and is intentionally allowed.
_FORBIDDEN_LIVE_CLAIMS: tuple[str, ...] = (
    "live_feedback=true",
    "live feedback",
    "feedback=live",
    "feedback=real",
)


class FeedbackRecord(BaseModel):
    """One transcript-shaped feedback event plus the evidence it asserts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feedback_id: str
    answer_id: str
    sentiment: Literal["positive", "negative"]
    language: Language
    query: str
    expected_filters: dict[str, str] = Field(default_factory=dict)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_answer_gist: str
    expected_abstain: bool = False
    reason: str | None = None
    query_id: str | None = None


class FeedbackFixture(BaseModel):
    """A labelled, offline set of feedback rows used as ingestion input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    feedback_fixture_id: str
    description: str
    source: str
    live_feedback: bool
    rows: list[FeedbackRecord]


def load_feedback_fixture(payload: Mapping[str, Any]) -> FeedbackFixture:
    """Parse and validate a feedback fixture, refusing any live-feedback claim."""
    try:
        fixture = FeedbackFixture.model_validate(dict(payload))
    except PydanticValidationError as exc:
        raise ValidationError(
            "Invalid feedback fixture payload", context={"errors": exc.errors()}
        ) from exc
    if fixture.source != FEEDBACK_SOURCE or fixture.live_feedback:
        raise ValidationError(
            "Feedback ingestion accepts only labelled offline fixture transcripts",
            context={"source": fixture.source, "live_feedback": fixture.live_feedback},
        )
    return fixture


def assert_offline_feedback_label(backend: str) -> str:
    """Return the backend label unchanged, rejecting claims of live feedback."""
    lowered = backend.lower()
    forbidden = next((claim for claim in _FORBIDDEN_LIVE_CLAIMS if claim in lowered), None)
    if forbidden is not None:
        raise ValidationError(
            "Backend label must not claim live feedback", context={"claim": forbidden}
        )
    return backend


def feedback_backend_label(backend: str) -> str:
    """Append the offline feedback-fixture provenance to a labelled backend.

    Idempotent: a caller may hand in the full label from configuration, and it
    is validated rather than duplicated (L1/L4).
    """
    checked = assert_offline_feedback_label(backend)
    markers = ("feedback=derived", FEEDBACK_BACKEND_MARKER, "live_feedback=False")
    missing = [marker for marker in markers if marker not in checked]
    if not missing:
        return checked
    return f"{checked}|" + "|".join(missing)


def ingest_feedback(
    golden: GoldenSet,
    fixture: FeedbackFixture,
    registry: FixtureRegistry,
    *,
    golden_id: str,
    description: str,
) -> GoldenSet:
    """Return a golden set extended with labelled, grounded feedback rows.

    Every derived row is checked before it is added: its id must be new, its
    expected chunk ids must resolve against the indexed fixture corpus (no
    dangling references, L12), and its abstention/filter shape must be coherent.
    An invalid row fails the whole ingestion rather than being silently skipped
    (L11/L13). Re-ingesting an already-extended set replaces its derived rows
    rather than duplicating them, so the published command is reproducible (L4).
    """
    fixture = load_feedback_fixture(fixture.model_dump(mode="json"))
    known_chunks = {
        chunk.chunk_id: doc.doc_id for doc in registry.documents for chunk in doc.chunks
    }
    derived_ids = {f"g-{row.feedback_id}" for row in fixture.rows}
    base_records = [
        record
        for record in golden.records
        if not (record.provenance == FEEDBACK_PROVENANCE and record.id in derived_ids)
    ]
    seen = {record.id for record in base_records}
    derived: list[GoldenRecord] = []
    for row in fixture.rows:
        if row.language not in REQUIRED_LANGUAGES:
            raise ValidationError(
                "Feedback row has an unsupported language",
                context={"feedback_id": row.feedback_id, "language": row.language.value},
            )
        record_id = f"g-{row.feedback_id}"
        if record_id in seen:
            raise ValidationError("Duplicate golden id", context={"record_id": record_id})
        seen.add(record_id)
        if row.expected_abstain and row.expected_chunk_ids:
            raise ValidationError(
                "An abstain feedback row cannot expect retrievable evidence",
                context={"feedback_id": row.feedback_id},
            )
        if not row.expected_abstain and not row.expected_chunk_ids:
            raise ValidationError(
                "An answerable feedback row must name expected evidence",
                context={"feedback_id": row.feedback_id},
            )
        unknown = [cid for cid in row.expected_chunk_ids if cid not in known_chunks]
        if unknown:
            raise ValidationError(
                "Feedback golden reference dangles against the fixture corpus",
                context={"feedback_id": row.feedback_id, "unknown_chunk_ids": unknown},
            )
        expected_docs = {known_chunks[cid] for cid in row.expected_chunk_ids}
        filter_doc = row.expected_filters.get("doc_id")
        if filter_doc is not None and filter_doc not in expected_docs:
            raise ValidationError(
                "Feedback filter doc_id disagrees with expected evidence",
                context={"feedback_id": row.feedback_id, "filter_doc_id": filter_doc},
            )
        derived.append(
            GoldenRecord(
                id=record_id,
                language=row.language,
                query=row.query,
                expected_filters=dict(row.expected_filters),
                expected_chunk_ids=list(row.expected_chunk_ids),
                expected_answer_gist=row.expected_answer_gist,
                expected_abstain=row.expected_abstain,
                provenance=FEEDBACK_PROVENANCE,
            )
        )
    return golden.model_copy(
        update={
            "golden_id": golden_id,
            "description": description,
            "records": [*base_records, *derived],
        }
    )


def feedback_row_counts(fixture: FeedbackFixture) -> dict[str, int]:
    """Return feedback rows per language, including zero-count languages (L7)."""
    counts = {language.value: 0 for language in REQUIRED_LANGUAGES}
    for row in fixture.rows:
        counts[row.language.value] += 1
    return counts


def feedback_derived_records(golden: GoldenSet) -> Sequence[GoldenRecord]:
    """Return only the rows labelled as feedback-derived."""
    return tuple(record for record in golden.records if record.provenance == FEEDBACK_PROVENANCE)
