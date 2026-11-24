"""Accuracy numbers are computed from labeled fixtures, not asserted as vibes (L1)."""

from _helpers import FIXTURE_ROOT

from uni_rag_core.fakes.object_store import FakeObjectStore
from uni_rag_ingestion.parsers.domain.accuracy import make_fixture_score, make_report
from uni_rag_ingestion.parsers.domain.models import PaperMetadata, QuestionSpan
from uni_rag_ingestion.parsers.service.evaluate import evaluate_fixture_corpus


def test_labeled_corpus_scores_are_derived_from_the_ground_truth_files() -> None:
    report = evaluate_fixture_corpus(FIXTURE_ROOT, make_store=FakeObjectStore)
    assert report.papers == 4
    assert report.segmentation.expected_questions == 11
    assert report.segmentation.predicted_questions == 11
    assert report.segmentation.matched_questions == 11
    assert report.segmentation.precision == 1.0
    assert report.segmentation.recall == 1.0
    assert report.segmentation.f1 == 1.0
    assert report.metadata.total_fields == 20
    assert report.metadata.correct_fields == 20
    assert report.metadata.accuracy == 1.0
    assert set(report.metadata.correct_by_field.values()) == {4}
    assert {item.fixture for item in report.per_fixture} == {
        "digital-past-paper.pdf",
        "digital-past-paper.html",
        "urdu-past-paper.html",
        "scanned-past-paper-page.png",
    }


def test_scoring_detects_mismatches_instead_of_claiming_perfection() -> None:
    metadata = PaperMetadata("CS-101", 2026, "Fall", "Midterm", "Computer Science")
    wrong = PaperMetadata("CS-101", 2026, "Spring", "Midterm", "Computer Science")
    expected = (QuestionSpan(1, "a", 1), QuestionSpan(2, "b", 1))
    predicted = (QuestionSpan(1, "wrong text", 1), QuestionSpan(3, "c", 1))
    report = make_report((make_fixture_score("probe", expected, predicted, metadata, wrong),))
    assert report.segmentation.matched_questions == 0
    assert report.segmentation.precision == 0.0
    assert report.segmentation.recall == 0.0
    assert report.segmentation.f1 == 0.0
    assert report.metadata.correct_fields == 4
    assert report.metadata.accuracy == 0.8
