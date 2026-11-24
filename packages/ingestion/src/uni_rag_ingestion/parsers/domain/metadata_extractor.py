"""Pure cover-page/header metadata extraction (L9)."""

from __future__ import annotations

import re
from typing import cast

from uni_rag_core.errors import ParseError
from uni_rag_ingestion.parsers.domain._digits import to_ascii_digits
from uni_rag_ingestion.parsers.domain.models import PaperMetadata

_COURSE_RE = re.compile(r"\b([A-Za-z]{2,5})\s*-?\s*([0-9]{3,4})\b")
_YEAR_RE = re.compile(r"\b(?:19|20)[0-9]{2}\b")
_TERM_RE = re.compile(r"\b(Fall|Spring|Summer|Autumn|Winter)\b", re.IGNORECASE)
_EXAM_RE = re.compile(r"\b(Mid-?term|Final|Quiz|Test)\b", re.IGNORECASE)
_DEPARTMENT_RE = re.compile(r"Department\s+of\s+([A-Za-z][A-Za-z& ]*[A-Za-z])", re.IGNORECASE)

_FIELDS = ("course_code", "year", "term", "exam_type", "department")


def extract_metadata(cover_text: str) -> PaperMetadata:
    """Extract the five labeled metadata fields from cover-page text.

    Raises:
        ParseError: if any mandatory field is absent; nothing is guessed (L13).
    """
    text = to_ascii_digits(cover_text)
    course = _COURSE_RE.search(text)
    year = _YEAR_RE.search(text)
    term = _TERM_RE.search(text)
    exam = _EXAM_RE.search(text)
    department = _DEPARTMENT_RE.search(text)

    values: dict[str, str | int | None] = {
        "course_code": f"{course.group(1).upper()}-{course.group(2)}" if course else None,
        "year": int(year.group(0)) if year else None,
        "term": term.group(1).title() if term else None,
        "exam_type": (_normalize_exam(exam.group(1)) if exam else None),
        "department": _title_ascii(department.group(1)) if department else None,
    }
    missing = [field for field in _FIELDS if values[field] is None]
    if missing:
        raise ParseError(
            "missing mandatory past-paper metadata",
            context={"missing_fields": missing},
        )

    return PaperMetadata(
        course_code=str(values["course_code"]),
        year=cast(int, values["year"]),
        term=str(values["term"]),
        exam_type=str(values["exam_type"]),
        department=str(values["department"]),
    )


def _normalize_exam(raw: str) -> str:
    compact = raw.replace("-", "").lower()
    if compact == "midterm":
        return "Midterm"
    if compact == "final":
        return "Final"
    return compact.title()


def _title_ascii(raw: str) -> str:
    return " ".join(word[:1].upper() + word[1:] for word in raw.lower().split())
