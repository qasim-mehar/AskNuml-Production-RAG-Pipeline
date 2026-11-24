"""Router language, intent and filter extraction specs (L7, L9)."""

from __future__ import annotations

import pytest

from packages.retrieval.tests.fixtures.corpus import build_corpus, golden_queries
from uni_rag_core import Language
from uni_rag_retrieval.domain.router import (
    Intent,
    detect_intent,
    detect_language,
    extract_filters,
    matches_filters,
    parse_route_response,
    route,
)


@pytest.mark.parametrize("row", golden_queries(), ids=lambda row: row["id"])
def test_router_classifies_every_golden_language(row: dict) -> None:
    assert detect_language(row["query"]) is Language(row["language"])
    assert route(row["query"]).language is Language(row["language"])


def test_router_extracts_course_year_and_exam_type() -> None:
    decision = route("When is the CS-101 midterm exam in 2026?")
    assert decision.filters.course_code == "CS-101"
    assert decision.filters.exam_type == "midterm"
    assert decision.filters.year == 2026
    assert decision.intent is Intent.EXAM_DATE


def test_router_extracts_department_as_metadata_not_a_branch() -> None:
    filters = extract_filters("What are the research interests of the computer science faculty?")
    assert filters.department == "cs"
    assert filters.as_mapping() == {"department": "cs"}
    faculty = next(chunk for chunk in build_corpus() if chunk.chunk_id == "chunk-faculty")
    assert matches_filters(faculty, filters)


def test_rule_fallback_when_llm_is_a_fake_or_abstains() -> None:
    text = "CS-101 ka instructor kaun hai?"
    assert route(text) == route(text, llm_response="Fake answer: NOT_CLASSIFIED")
    assert parse_route_response("NOT_CLASSIFIED") is None
    assert parse_route_response("not json at all") is None


def test_router_accepts_a_valid_llm_classification() -> None:
    response = '```json{"language": "ur", "intent": "exam_date", "filters": {"course_code": "CS-101", "year": 2026}}```'
    decision = route("CS-101 کا امتحان کب ہے؟", llm_response=response)
    assert decision.language is Language.UR
    assert decision.intent is Intent.EXAM_DATE
    assert decision.filters.course_code == "CS-101"
    assert decision.filters.year == 2026


def test_intent_keywords_are_deterministic() -> None:
    assert detect_intent("Who is the instructor for CS-101?") is Intent.FACULTY_INFO
    assert detect_intent("How many credits is CS-101?") is Intent.COURSE_INFO
    assert detect_intent("Tell me a campus story") is Intent.GENERAL
