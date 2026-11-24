"""Score the labeled fixture corpus through the real pipeline (L1).

This is reusable golden material for Lane F; it reads only checked-in fixtures
and returns computed numbers, never estimates.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from uni_rag_core import DocType, Document, Language
from uni_rag_core.errors import ParseError
from uni_rag_core.ports.object_store import ObjectStore
from uni_rag_ingestion.parsers.adapters.docling_parser import DoclingParser
from uni_rag_ingestion.parsers.adapters.mineru_parser import MinerUParser
from uni_rag_ingestion.parsers.domain.accuracy import (
    AccuracyReport,
    FixtureScore,
    make_fixture_score,
    make_report,
)
from uni_rag_ingestion.parsers.domain.models import (
    DocumentParser,
    PaperMetadata,
    QuestionSpan,
    TableRecord,
)
from uni_rag_ingestion.parsers.service.parse import parse_document

_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


class ExpectedQuestion(BaseModel):
    """A labeled question in a ground-truth fixture."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question_number: int
    page: int
    text: str
    options: list[str] = Field(default_factory=list)


class ExpectedMetadata(BaseModel):
    """Labeled metadata values for one fixture paper."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    course_code: str
    year: int
    term: str
    exam_type: str
    department: str

    def to_domain(self) -> PaperMetadata:
        """Convert to the pure domain value object used for scoring."""
        return PaperMetadata(
            course_code=self.course_code,
            year=self.year,
            term=self.term,
            exam_type=self.exam_type,
            department=self.department,
        )


class ExpectedTable(BaseModel):
    """Labeled table structure for one fixture paper."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page: int
    header: list[str]
    rows: list[list[str]]

    def to_domain(self) -> TableRecord:
        """Convert to the pure table record used for comparison."""
        return TableRecord(
            page=self.page,
            header=tuple(self.header),
            rows=tuple(tuple(row) for row in self.rows),
        )


class FixtureSpec(BaseModel):
    """One labeled paper, loaded from ``expected/*.json``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture: str
    source_kind: str
    source_path: str
    transcription_path: str | None = None
    image_source: str | None = None
    doc_id: str
    source_url: str
    title: str
    doc_type: DocType
    language: Language
    expected_page_count: int
    expected_metadata: ExpectedMetadata
    expected_questions: list[ExpectedQuestion]
    expected_tables: list[ExpectedTable]


def _resolve(root: Path, value: str) -> Path:
    """Resolve a fixture path relative to the corpus root or the repository root."""
    direct = root / value
    if direct.exists():
        return direct
    repository_relative = root.parents[2] / value
    if repository_relative.exists():
        return repository_relative
    raise ParseError("fixture path does not exist", context={"value": value, "root": str(root)})


def _load_specs(root: Path) -> list[FixtureSpec]:
    paths = sorted((root / "expected").glob("*.json"))
    if not paths:
        raise ParseError("no ground-truth fixtures found", context={"root": str(root)})
    specs: list[FixtureSpec] = []
    for path in paths:
        try:
            specs.append(FixtureSpec.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValidationError, UnicodeError) as exc:
            raise ParseError(
                "invalid ground-truth fixture",
                context={"path": str(path)},
            ) from exc
    return specs


def _build_parser(spec: FixtureSpec, root: Path) -> DocumentParser:
    if spec.source_kind in {"docling-pdf", "docling-html"}:
        return DoclingParser(prefer_docling=False)
    if spec.source_kind == "mineru-transcription":
        if spec.transcription_path is None:
            raise ParseError(
                "scanned fixture has no transcription", context={"fixture": spec.fixture}
            )
        return MinerUParser(transcription_path=_resolve(root, spec.transcription_path))
    raise ParseError(
        "unknown fixture source kind", context={"fixture": spec.fixture, "kind": spec.source_kind}
    )


def evaluate_fixture_corpus(
    root: Path,
    *,
    make_store: Callable[[], ObjectStore],
) -> AccuracyReport:
    """Run every labeled paper through parsing and score it.

    Args:
        root: directory containing ``expected/*.json`` and the fixture files.
        make_store: factory for a fresh ObjectStore per paper (fakes in tests).

    Raises:
        ParseError: when a fixture is invalid or the pipeline fails.
    """
    scores: list[FixtureScore] = []
    for spec in _load_specs(root):
        source_path = _resolve(root, spec.source_path)
        outcome = parse_document(
            Document(
                doc_id=spec.doc_id,
                source_url=spec.source_url,
                title=spec.title,
                doc_type=spec.doc_type,
                last_crawled=_FIXED_TIME,
                content_hash=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                language=spec.language,
            ),
            source_path=source_path,
            parser=_build_parser(spec, root),
            object_store=make_store(),
        )
        if len(outcome.image_refs) != spec.expected_page_count:
            raise ParseError(
                "page/image count does not match fixture",
                context={
                    "fixture": spec.fixture,
                    "expected": spec.expected_page_count,
                    "actual": len(outcome.image_refs),
                },
            )
        expected = tuple(
            QuestionSpan(item.question_number, item.text, item.page, tuple(item.options))
            for item in spec.expected_questions
        )
        predicted = tuple(
            QuestionSpan(item.question_number, item.text, item.page, tuple(item.options))
            for item in outcome.questions
        )
        scores.append(
            make_fixture_score(
                spec.fixture,
                expected,
                predicted,
                spec.expected_metadata.to_domain(),
                outcome.metadata,
            )
        )
    return make_report(scores)
