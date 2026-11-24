"""Golden-set format, validation and grounding tests (L7/L12)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from eval_helpers import load_fixture

from uni_rag_core.errors import ValidationError
from uni_rag_eval.domain.golden import (
    chunks_from_registry,
    load_fixture_registry,
    load_golden_set,
    validate_golden_set,
)
from uni_rag_eval.runner.harness import language_counts

ROOT = Path(__file__).resolve().parents[3]
VERIFIED = {"tests/fixtures/html/course-page.html"}


def _synthetic() -> tuple[Any, Any]:
    return load_golden_set(load_fixture("synthetic-golden.json")), load_fixture_registry(
        load_fixture("synthetic-registry.json")
    )


def test_synthetic_golden_fixture_parses_and_validates() -> None:
    golden, registry = _synthetic()
    validate_golden_set(golden, registry, VERIFIED)
    assert golden.golden_id == "synthetic-oracle-v1"
    assert language_counts(golden) == {"en": 2, "ur": 1, "roman_urdu": 1}


@pytest.mark.parametrize(
    ("mutate", "expected_message"),
    [
        (
            lambda data: data["records"][0].update(expected_chunk_ids=["unknown"]),
            "outside the fixture corpus",
        ),
        (
            lambda data: data["records"].append(
                {**data["records"][0], "id": "s5", "language": "en"}
            ),
            "not balanced",
        ),
        (
            lambda data: data["records"][1].update(expected_abstain=False),
            "An answerable record",
        ),
        (
            lambda data: data["records"][1].update(expected_abstain=True, expected_chunk_ids=["c"]),
            "An abstain record",
        ),
        (
            lambda data: data["records"][0].update(expected_filters={"doc_id": "doc-other"}),
            "disagrees",
        ),
        (lambda data: data["records"][0].update(query=""), "must be non-empty"),
    ],
)
def test_validation_rejects_invalid_golden_records(mutate: Any, expected_message: str) -> None:
    payload = load_fixture("synthetic-golden.json")
    mutate(payload)
    golden, registry = _synthetic()
    with pytest.raises(ValidationError, match=expected_message):
        validate_golden_set(load_golden_set(payload), registry, VERIFIED)


def test_validation_rejects_missing_fixture_source() -> None:
    golden, registry = _synthetic()
    with pytest.raises(ValidationError, match="do not exist"):
        validate_golden_set(golden, registry, set())


def test_a_language_with_zero_questions_is_an_error() -> None:
    payload = deepcopy(load_fixture("synthetic-golden.json"))
    payload["records"] = [record for record in payload["records"] if record["language"] != "ur"]
    golden, registry = _synthetic()
    with pytest.raises(ValidationError, match="needs golden questions"):
        validate_golden_set(load_golden_set(payload), registry, VERIFIED)


def test_curated_golden_set_is_balanced_and_grounded() -> None:
    golden = load_golden_set(
        json.loads((ROOT / "eval/golden/golden.json").read_text(encoding="utf-8"))
    )
    registry = load_fixture_registry(
        json.loads((ROOT / "eval/golden/fixture-registry.json").read_text(encoding="utf-8"))
    )
    verified = {doc.source_path for doc in registry.documents if (ROOT / doc.source_path).is_file()}
    validate_golden_set(golden, registry, verified)
    assert len(golden.records) == 30
    assert language_counts(golden) == {"en": 10, "ur": 10, "roman_urdu": 10}
    assert {record.language.value for record in golden.records} == {
        "en",
        "ur",
        "roman_urdu",
    }


def test_curated_golden_chunk_refs_resolve_against_the_integrated_corpus() -> None:
    golden = load_golden_set(
        json.loads((ROOT / "eval/golden/golden.json").read_text(encoding="utf-8"))
    )
    registry = load_fixture_registry(
        json.loads((ROOT / "eval/golden/fixture-registry.json").read_text(encoding="utf-8"))
    )
    indexed = {chunk.chunk_id for chunk in chunks_from_registry(registry)}
    referenced = {cid for record in golden.records for cid in record.expected_chunk_ids}
    assert referenced, "the golden set must name expected chunk ids"
    assert referenced <= indexed, "golden references must not dangle against the indexed corpus"
    answerable = [record for record in golden.records if not record.expected_abstain]
    assert len(answerable) == 27


def test_a_declared_chunk_hash_that_disagrees_with_its_text_is_rejected() -> None:
    registry = load_fixture_registry(load_fixture("synthetic-registry.json"))
    doc = registry.documents[0]
    bad_chunk = doc.chunks[0].model_copy(update={"content_hash": "not-the-real-hash"})
    bad_doc = doc.model_copy(update={"chunks": [bad_chunk, *doc.chunks[1:]]})
    mutated = registry.model_copy(update={"documents": [bad_doc, *registry.documents[1:]]})
    with pytest.raises(ValidationError, match="content hash disagrees"):
        chunks_from_registry(mutated)


def test_registry_chunks_carry_full_l6_metadata() -> None:
    _, registry = _synthetic()
    chunks = chunks_from_registry(registry)
    assert len(chunks) == 5
    assert all(chunk.source_url and chunk.heading_path for chunk in chunks)
    assert all(chunk.content_hash for chunk in chunks)
    assert all(chunk.last_crawled.tzinfo is not None for chunk in chunks)
    assert all(chunk.doc_type.value == "web_page" for chunk in chunks)
    assert all(chunk.version == "v1" for chunk in chunks)
