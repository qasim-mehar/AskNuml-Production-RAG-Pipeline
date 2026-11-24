"""Foundation fixtures are real, valid files."""

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class _HeadingCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3"}:
            self.headings.append(tag)


@pytest.mark.parametrize(
    "name",
    ["course-page.html", "faculty-page.html", "announcements-page.html"],
)
def test_html_fixtures_are_valid(name: str) -> None:
    raw = (FIXTURES / "html" / name).read_text(encoding="utf-8")
    parser = _HeadingCollector()
    parser.feed(raw)
    assert "<html" in raw.lower()
    assert parser.headings


def test_pdf_fixture_is_valid() -> None:
    assert (FIXTURES / "pdf" / "digital-course-outline.pdf").read_bytes().startswith(b"%PDF-")


def test_png_fixture_is_valid() -> None:
    assert (
        (FIXTURES / "pdf" / "scanned-past-paper-page.png")
        .read_bytes()
        .startswith(b"\x89PNG\r\n\x1a\n")
    )


def test_mini_golden_set_has_ten_multilingual_questions() -> None:
    data = json.loads((FIXTURES / "golden" / "mini-golden.json").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 10
    languages = {item["language"] for item in data}
    assert {"en", "ur", "roman_urdu"} <= languages
    for item in data:
        assert set(item) >= {
            "id",
            "query",
            "language",
            "expected_doc_ids",
            "expected_page",
            "expected_answer_snippet",
        }
