"""ADR 0010: the fake reproduces the blocker's exact payload collision.

The reusable invariant helper ``assert_vector_payload_roundtrip_contract`` is
wired into the canonical fake suite in ``test_core_fakes.py`` and is what Lane
D's Qdrant adapter must call on the integration re-run.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tests.factories import chunk
from uni_rag_core import Chunk, FakeVectorStore
from uni_rag_core.fakes.vector_store import (
    OPERATIONAL_FIELDS,
    stored_payload,
    strip_operational_fields,
)

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def test_fake_stored_payload_carries_every_blocker_field() -> None:
    """The fake carries the blocker's exact operational field list (L4)."""
    sample = chunk()
    stored = stored_payload(sample)
    assert set(OPERATIONAL_FIELDS) <= set(stored)
    assert stored == stored_payload(sample)
    assert {field: stored[field] for field in OPERATIONAL_FIELDS} == {
        "last_crawled_ts": FIXED.timestamp(),
        "department": "General",
        "course_code": "GEN-000",
        "year": "0",
        "term": "N/A",
        "is_live": True,
        "indexed_at": "2026-01-01T00:00:00+00:00",
        "deleted_at": None,
        "superseded_by": None,
    }


def test_stored_payload_is_the_exact_collision() -> None:
    """The raw stored payload is what raised extra_forbidden at 512be58."""
    stored = stored_payload(chunk())
    with pytest.raises(ValidationError) as excinfo:
        Chunk.model_validate(stored)
    assert any(error["type"] == "extra_forbidden" for error in excinfo.value.errors())
    assert Chunk.model_validate(strip_operational_fields(stored)) == chunk()


def test_returned_hit_payload_has_no_operational_fields() -> None:
    """Operational fields stay in storage; the port carries domain data only."""
    store = FakeVectorStore()
    sample = chunk()
    store.upsert([(sample, [1.0, 0.0])])
    hit = store.search([1.0, 0.0], top_k=1)[0]
    assert not set(OPERATIONAL_FIELDS) & set(hit.payload)
    assert hit.payload == sample.model_dump(mode="json")
