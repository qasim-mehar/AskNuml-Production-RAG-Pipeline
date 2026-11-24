"""Table integrity pins: whole records, all cells, Urdu text unchanged (L1, L7)."""

import pytest
from _helpers import load_spec, resolve_fixture

from uni_rag_core.errors import ParseError
from uni_rag_ingestion.parsers.adapters._fixture_extract import parse_html_fixture
from uni_rag_ingestion.parsers.domain.models import ParsedTable
from uni_rag_ingestion.parsers.domain.table_extractor import normalize_tables


@pytest.mark.parametrize(
    "spec_name,fixture",
    [
        ("digital-past-paper-html.json", "digital-past-paper.html"),
        ("urdu-past-paper.json", "urdu-past-paper.html"),
    ],
)
def test_html_table_survives_as_a_whole_row_and_column_record(spec_name: str, fixture: str) -> None:
    spec = load_spec(spec_name)
    parsed = parse_html_fixture(resolve_fixture(fixture))
    actual = normalize_tables(parsed.pages[0].tables)
    expected = tuple(item.to_domain() for item in spec.expected_tables)
    assert actual == expected


def test_urdu_table_cells_round_trip_byte_for_byte() -> None:
    parsed = parse_html_fixture(resolve_fixture("urdu-past-paper.html"))
    table = normalize_tables(parsed.pages[0].tables)[0]
    assert table.header[0].encode("utf-8") == "سوال".encode()
    assert table.rows[0][1].encode("utf-8") == "۲۰".encode()


def test_ragged_table_is_rejected_instead_of_padded() -> None:
    with pytest.raises(ParseError) as raised:
        normalize_tables((ParsedTable(page=1, header=("A", "B"), rows=(("1",),)),))
    assert raised.value.context["header_width"] == 2
