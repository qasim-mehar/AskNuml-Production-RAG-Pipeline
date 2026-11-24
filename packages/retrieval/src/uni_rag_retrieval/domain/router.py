"""Pure language/intent classification and filter extraction (L7, L9).

The LLM port is optional: when a provider declines or returns anything other
than the agreed JSON, :func:`route` falls back to the deterministic rule-based
reading. No provider calls are made from this module.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum

from uni_rag_core.schemas import Chunk, Language
from uni_rag_retrieval.domain.normalize import is_urdu_script, looks_roman_urdu, normalize, tokens

_COURSE_CODE = re.compile(r"\b([A-Za-z]{2,4})-?(\d{3})\b")
_YEAR = re.compile(r"\b(20\d{2})\b")

_DEPARTMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "cs": ("cs", "computer science"),
    "math": ("math", "mathematics"),
}

_EXAM_TERMS = ("midterm", "final", "quiz")
_TERM_TERMS = ("fall", "spring", "summer")


class Intent(StrEnum):
    """Coarse query intent; used only to explain retrieval decisions."""

    COURSE_INFO = "course_info"
    EXAM_DATE = "exam_date"
    FACULTY_INFO = "faculty_info"
    GENERAL = "general"


@dataclass(frozen=True)
class FilterSet:
    """Structured metadata filters extracted from a query."""

    department: str | None = None
    course_code: str | None = None
    year: int | None = None
    term: str | None = None
    exam_type: str | None = None

    def as_mapping(self) -> dict[str, str]:
        """Return only populated filters as strings, in a stable order."""
        values: dict[str, str] = {}
        if self.department is not None:
            values["department"] = self.department
        if self.course_code is not None:
            values["course_code"] = self.course_code
        if self.year is not None:
            values["year"] = str(self.year)
        if self.term is not None:
            values["term"] = self.term
        if self.exam_type is not None:
            values["exam_type"] = self.exam_type
        return values


@dataclass(frozen=True)
class RouteDecision:
    """The output of the route stage, consumed by filter and search."""

    language: Language
    intent: Intent
    filters: FilterSet
    normalized_text: str


def detect_language(text: str) -> Language:
    """Classify a query as English, Urdu or Roman Urdu (L7)."""
    if is_urdu_script(text):
        return Language.UR
    if looks_roman_urdu(tokens(normalize(text))):
        return Language.ROMAN_URDU
    return Language.EN


def extract_filters(text: str) -> FilterSet:
    """Extract department, course code, year, term and exam type from ``text``."""
    lowered = " ".join(tokens(normalize(text)))
    course = _COURSE_CODE.search(text)
    year = _YEAR.search(text)
    department = next(
        (
            name
            for name, aliases in _DEPARTMENT_ALIASES.items()
            if any(alias in lowered for alias in aliases)
        ),
        None,
    )
    return FilterSet(
        department=department,
        course_code=f"{course.group(1).upper()}-{course.group(2)}" if course else None,
        year=int(year.group(1)) if year else None,
        term=next((term for term in _TERM_TERMS if term in lowered), None),
        exam_type=next((term for term in _EXAM_TERMS if term in lowered), None),
    )


def detect_intent(text: str) -> Intent:
    """Classify intent with a deterministic keyword reading."""
    lowered = " ".join(tokens(normalize(text)))
    if any(term in lowered for term in _EXAM_TERMS):
        return Intent.EXAM_DATE
    if any(term in lowered for term in ("instructor", "teacher", "faculty", "research")):
        return Intent.FACULTY_INFO
    if any(term in lowered for term in ("credit", "course", "outcome", "learning")):
        return Intent.COURSE_INFO
    return Intent.GENERAL


def route(text: str, *, llm_response: str | None = None) -> RouteDecision:
    """Route ``text``; prefer a valid LLM JSON response, else use rules."""
    decision = parse_route_response(llm_response) if llm_response is not None else None
    if decision is not None:
        return RouteDecision(
            language=decision.language,
            intent=decision.intent,
            filters=decision.filters,
            normalized_text=normalize(text, language=decision.language),
        )
    language = detect_language(text)
    return RouteDecision(
        language=language,
        intent=detect_intent(text),
        filters=extract_filters(text),
        normalized_text=normalize(text, language=language),
    )


def parse_route_response(raw: str) -> RouteDecision | None:
    """Parse the router LLM's JSON, returning None for any unusable response."""
    candidate = raw.strip().removeprefix("```json").removesuffix("```").strip()
    if not candidate.startswith("{"):
        return None
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        language = Language(str(payload["language"]))
        intent = Intent(str(payload["intent"]))
        raw_filters = payload.get("filters", {})
    except (KeyError, ValueError):
        return None
    if not isinstance(raw_filters, dict):
        return None
    filters = FilterSet(
        department=_optional_string(raw_filters.get("department")),
        course_code=_optional_string(raw_filters.get("course_code")),
        year=_optional_int(raw_filters.get("year")),
        term=_optional_string(raw_filters.get("term")),
        exam_type=_optional_string(raw_filters.get("exam_type")),
    )
    return RouteDecision(language=language, intent=intent, filters=filters, normalized_text="")


def _optional_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def matches_filters(chunk: Chunk, filters: FilterSet) -> bool:
    """Return True when a chunk satisfies every extracted metadata filter."""
    haystack = normalize(
        " ".join(
            [
                chunk.doc_id,
                chunk.source_url,
                chunk.version,
                chunk.doc_type.value,
                chunk.language.value,
                *chunk.heading_path,
                chunk.text,
            ]
        )
    )
    for key, value in filters.as_mapping().items():
        if key == "department":
            aliases = _DEPARTMENT_ALIASES.get(value, (value,))
            if not any(normalize(alias) in haystack for alias in aliases):
                return False
        elif normalize(value) not in haystack:
            return False
    return True
