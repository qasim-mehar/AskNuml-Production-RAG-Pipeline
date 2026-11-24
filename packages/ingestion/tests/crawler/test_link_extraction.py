"""Link-capture specs: page, PDF and image links plus document typing."""

from packages.ingestion.tests.crawler.conftest import BASE_URL, fixture_text
from uni_rag_core import DocType
from uni_rag_ingestion.crawler.domain import doc_type_for, extract_links


def test_pdf_and_image_links_are_captured_with_page_links() -> None:
    links = extract_links(fixture_text("pdf-links-page.html"), f"{BASE_URL}/")
    assert links.page_links == (
        f"{BASE_URL}/private/internal",
        f"{BASE_URL}/courses/cs-101",
        f"{BASE_URL}/footer-link",
    )
    assert links.pdf_links == (f"{BASE_URL}/docs/course-outline.pdf",)
    assert links.image_links == (f"{BASE_URL}/images/past-paper-1.png",)


def test_relative_links_resolve_against_base_url() -> None:
    links = extract_links(
        '<a href="sibling.html">sibling</a><img src="images/p.png" />',
        f"{BASE_URL}/courses/cs-101",
    )
    assert links.page_links == (f"{BASE_URL}/courses/sibling.html",)
    assert links.image_links == (f"{BASE_URL}/courses/images/p.png",)


def test_doc_type_for_pdf_and_html() -> None:
    assert doc_type_for(f"{BASE_URL}/a.PDF") is DocType.PDF
    assert doc_type_for(f"{BASE_URL}/", "text/html; charset=utf-8") is DocType.WEB_PAGE
    assert doc_type_for(f"{BASE_URL}/data.bin", "application/octet-stream") is DocType.OTHER
