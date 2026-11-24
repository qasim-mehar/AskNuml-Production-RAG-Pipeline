"""Ground truth is labeled before the extractor exists (L12)."""

from pathlib import Path

from _helpers import FIXTURE_ROOT, load_spec, resolve_fixture


def test_ground_truth_corpus_labels_four_papers_and_eleven_questions() -> None:
    specs = [load_spec(path.name) for path in sorted((FIXTURE_ROOT / "expected").glob("*.json"))]
    assert len(specs) == 4
    assert sum(len(spec.expected_questions) for spec in specs) == 11
    for spec in specs:
        assert spec.expected_metadata.course_code
        assert spec.expected_page_count >= 1
        assert spec.expected_questions
        assert all(question.text for question in spec.expected_questions)
        assert resolve_fixture(spec.source_path).is_file()


def test_ground_truth_preserves_urdu_code_points_byte_for_byte() -> None:
    spec = load_spec("urdu-past-paper.json")
    assert spec.expected_questions[0].text.encode("utf-8") == "نظم کی تعریف کریں۔".encode()
    assert spec.expected_tables[0].rows[0][1].encode("utf-8") == "۲۰".encode()


def test_scanned_page_label_uses_a_transcription_and_the_png_fixture() -> None:
    spec = load_spec("scanned-past-paper.json")
    assert spec.source_kind == "mineru-transcription"
    assert spec.transcription_path is not None
    assert Path(spec.transcription_path).name == "scanned-past-paper-transcription.txt"
    assert resolve_fixture(str(spec.image_source)).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
