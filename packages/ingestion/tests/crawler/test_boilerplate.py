"""Boilerplate spec: chrome is stripped while the main article survives."""

from packages.ingestion.tests.crawler.conftest import fixture_text
from uni_rag_ingestion.crawler.domain import extract_main_content


def test_boilerplate_is_stripped_while_main_content_survives() -> None:
    content = extract_main_content(fixture_text("boilerplate-page.html"))
    assert content.title == "Admissions"
    assert content.text == "Admissions Applications close on 2026-12-01. Submit the form."
    assert "Navigation" not in content.text
    assert "Copyright" not in content.text
    assert "ignore me" not in content.text
