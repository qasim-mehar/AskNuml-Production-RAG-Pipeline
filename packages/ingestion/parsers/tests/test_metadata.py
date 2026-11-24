"""Metadata extraction pins: labeled values, Urdu digits, typed failure (L1, L7, L13)."""

import pytest
from _helpers import load_spec, parser_for, resolve_fixture

from uni_rag_core.errors import ParseError
from uni_rag_ingestion.parsers.domain.metadata_extractor import extract_metadata

_SPECS = [
    "digital-past-paper.json",
    "digital-past-paper-html.json",
    "urdu-past-paper.json",
    "scanned-past-paper.json",
]


@pytest.mark.parametrize("spec_name", _SPECS)
def test_cover_metadata_matches_every_labeled_value(spec_name: str) -> None:
    spec = load_spec(spec_name)
    parsed = parser_for(spec).parse(resolve_fixture(spec.source_path))
    actual = extract_metadata(parsed.pages[0].text)
    assert actual.as_dict() == spec.expected_metadata.to_domain().as_dict()


def test_urdu_indic_digits_in_year_are_normalized_without_losing_urdu_text() -> None:
    metadata = extract_metadata("URD-101 Final Examination\nDepartment of Urdu\nFall ۲۰۲۴\n")
    assert metadata.year == 2024
    assert metadata.term == "Fall"
    assert metadata.department == "Urdu"


def test_missing_metadata_field_raises_a_typed_error_without_guessing() -> None:
    with pytest.raises(ParseError) as raised:
        extract_metadata("CS-101 Course Outline\nDepartment of Computer Science\nFall 2026\n")
    assert raised.value.context["missing_fields"] == ["exam_type"]
