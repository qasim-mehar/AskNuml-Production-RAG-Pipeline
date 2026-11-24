"""Question segmentation pins: exact counts, numbering patterns, no skips (L1, L7)."""

import pytest
from _helpers import load_spec, parser_for, resolve_fixture

from uni_rag_core.errors import ParseError
from uni_rag_ingestion.parsers.domain.models import ParsedPage
from uni_rag_ingestion.parsers.domain.question_segmenter import segment_questions
from uni_rag_ingestion.parsers.service.evaluate import FixtureSpec

_SPECS = [
    "digital-past-paper.json",
    "digital-past-paper-html.json",
    "urdu-past-paper.json",
    "scanned-past-paper.json",
]


def _labeled_pages(spec_name: str) -> tuple[tuple[ParsedPage, ...], FixtureSpec]:
    spec = load_spec(spec_name)
    parsed = parser_for(spec).parse(resolve_fixture(spec.source_path))
    return parsed.pages, spec


@pytest.mark.parametrize("spec_name", _SPECS)
def test_fixture_segments_into_exactly_the_labeled_question_count(spec_name: str) -> None:
    pages, spec = _labeled_pages(spec_name)
    assert len(segment_questions(pages)) == len(spec.expected_questions)


@pytest.mark.parametrize("spec_name", _SPECS)
def test_question_number_page_and_text_match_the_label(spec_name: str) -> None:
    pages, spec = _labeled_pages(spec_name)
    spans = segment_questions(pages)
    expected = [(q.question_number, q.page, q.text) for q in spec.expected_questions]
    actual = [(span.question_number, span.page, span.text) for span in spans]
    assert actual == expected


def test_segmenter_accepts_q_prefix_plain_number_and_urdu_numerals() -> None:
    pages = (
        ParsedPage(
            page=1,
            text="Q1. alpha\n2. beta\nسوال ۳: gamma\nQ4) delta\n",
        ),
    )
    spans = segment_questions(pages)
    assert [(span.question_number, span.text) for span in spans] == [
        (1, "alpha"),
        (2, "beta"),
        (3, "gamma"),
        (4, "delta"),
    ]


def test_repeated_marker_is_a_continuation_not_a_second_record() -> None:
    pages = (ParsedPage(page=1, text="Q1. first line\nQ1. continued text\nQ2. second\n"),)
    spans = segment_questions(pages)
    assert len(spans) == 2
    assert spans[0].text == "first line\nQ1. continued text"


def test_option_lines_attach_to_the_open_question() -> None:
    pages = (ParsedPage(page=1, text="Q1. Pick one.\n(a) alpha\n(b) beta\nQ2. Next.\n"),)
    spans = segment_questions(pages)
    assert spans[0].options == ("a) alpha", "b) beta")
    assert spans[1].options == ()


def test_text_without_question_markers_raises_a_typed_error() -> None:
    with pytest.raises(ParseError) as raised:
        segment_questions((ParsedPage(page=1, text="A course outline with no questions.\n"),))
    assert "no question markers" in raised.value.message
    assert raised.value.context["pages"] == 1
