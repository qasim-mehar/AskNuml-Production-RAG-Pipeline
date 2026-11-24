"""Pure scoring of segmentation and metadata against labeled fixtures (L1)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from uni_rag_core.errors import ParseError
from uni_rag_ingestion.parsers.domain.models import PaperMetadata, QuestionSpan

METADATA_FIELDS: tuple[str, ...] = (
    "course_code",
    "year",
    "term",
    "exam_type",
    "department",
)


@dataclass(frozen=True, slots=True)
class SegmentationScore:
    """Corpus-level question segmentation metrics."""

    papers: int
    expected_questions: int
    predicted_questions: int
    matched_questions: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True, slots=True)
class MetadataScore:
    """Corpus-level metadata extraction metrics."""

    papers: int
    fields: tuple[str, ...]
    correct_fields: int
    total_fields: int
    accuracy: float
    correct_by_field: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FixtureScore:
    """Score for one labeled paper; provenance for the corpus report."""

    fixture: str
    expected_questions: int
    predicted_questions: int
    matched_questions: int
    segmentation_accuracy: float
    metadata_correct: int
    metadata_total: int
    metadata_correct_by_field: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AccuracyReport:
    """Numbers reported in the Lane B handoff, computed from fixtures only."""

    papers: int
    segmentation: SegmentationScore
    metadata: MetadataScore
    per_fixture: tuple[FixtureScore, ...]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable view for Lane F golden material."""
        return {
            "papers": self.papers,
            "segmentation": {
                "expected_questions": self.segmentation.expected_questions,
                "predicted_questions": self.segmentation.predicted_questions,
                "matched_questions": self.segmentation.matched_questions,
                "precision": self.segmentation.precision,
                "recall": self.segmentation.recall,
                "f1": self.segmentation.f1,
            },
            "metadata": {
                "fields": list(self.metadata.fields),
                "correct_fields": self.metadata.correct_fields,
                "total_fields": self.metadata.total_fields,
                "accuracy": self.metadata.accuracy,
                "correct_by_field": dict(self.metadata.correct_by_field),
            },
            "per_fixture": [
                {
                    "fixture": item.fixture,
                    "expected_questions": item.expected_questions,
                    "predicted_questions": item.predicted_questions,
                    "matched_questions": item.matched_questions,
                    "segmentation_accuracy": item.segmentation_accuracy,
                    "metadata_correct": item.metadata_correct,
                    "metadata_total": item.metadata_total,
                }
                for item in self.per_fixture
            ],
        }


def count_matched_questions(
    expected: Sequence[QuestionSpan],
    predicted: Sequence[QuestionSpan],
) -> int:
    """Match questions by (number, page, text) as a multiset.

    Text is part of the key so correct numbering with corrupted question text
    cannot be reported as perfect extraction (L1, L7).
    """
    expected_keys = Counter((item.question_number, item.page, item.text) for item in expected)
    predicted_keys = Counter((item.question_number, item.page, item.text) for item in predicted)
    return sum((expected_keys & predicted_keys).values())


def score_metadata_fields(expected: PaperMetadata, actual: PaperMetadata) -> dict[str, bool]:
    """Compare each labeled metadata field; no field is inferred or skipped."""
    labeled = expected.as_dict()
    produced = actual.as_dict()
    return {name: labeled[name] == produced[name] for name in METADATA_FIELDS}


def make_fixture_score(
    fixture: str,
    expected: Sequence[QuestionSpan],
    predicted: Sequence[QuestionSpan],
    expected_metadata: PaperMetadata,
    actual_metadata: PaperMetadata,
) -> FixtureScore:
    """Score one fixture against its ground truth."""
    expected_count = len(expected)
    predicted_count = len(predicted)
    matched = count_matched_questions(expected, predicted)
    denominator = max(expected_count, predicted_count)
    if denominator == 0:
        raise ParseError("fixture has no questions to score", context={"fixture": fixture})
    fields = score_metadata_fields(expected_metadata, actual_metadata)
    return FixtureScore(
        fixture=fixture,
        expected_questions=expected_count,
        predicted_questions=predicted_count,
        matched_questions=matched,
        segmentation_accuracy=matched / denominator,
        metadata_correct=sum(fields.values()),
        metadata_total=len(fields),
        metadata_correct_by_field={name: int(correct) for name, correct in fields.items()},
    )


def make_report(scores: Sequence[FixtureScore]) -> AccuracyReport:
    """Aggregate per-fixture scores into the corpus numbers (L1)."""
    expected_count = sum(item.expected_questions for item in scores)
    predicted_count = sum(item.predicted_questions for item in scores)
    matched = sum(item.matched_questions for item in scores)
    precision = matched / predicted_count if predicted_count else 0.0
    recall = matched / expected_count if expected_count else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
    correct = sum(item.metadata_correct for item in scores)
    total = sum(item.metadata_total for item in scores)
    correct_by_field = {
        name: sum(item.metadata_correct_by_field.get(name, 0) for item in scores)
        for name in METADATA_FIELDS
    }
    return AccuracyReport(
        papers=len(scores),
        segmentation=SegmentationScore(
            papers=len(scores),
            expected_questions=expected_count,
            predicted_questions=predicted_count,
            matched_questions=matched,
            precision=precision,
            recall=recall,
            f1=f1,
        ),
        metadata=MetadataScore(
            papers=len(scores),
            fields=METADATA_FIELDS,
            correct_fields=correct,
            total_fields=total,
            accuracy=correct / total if total else 0.0,
            correct_by_field=correct_by_field,
        ),
        per_fixture=tuple(scores),
    )
