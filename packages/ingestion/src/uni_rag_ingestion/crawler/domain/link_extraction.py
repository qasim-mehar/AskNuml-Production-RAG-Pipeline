"""Page, PDF and image link capture from HTML (L9)."""

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from uni_rag_core.schemas import DocType

_PDF_SUFFIX = ".pdf"
_PAGE_SUFFIXES = (".html", ".htm", ".shtml")


def _is_pdf(url: str) -> bool:
    return urlsplit(url).path.lower().endswith(_PDF_SUFFIX)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


@dataclass(frozen=True)
class ExtractedLinks:
    """Absolute, de-duplicated links in document order."""

    page_links: tuple[str, ...]
    pdf_links: tuple[str, ...]
    image_links: tuple[str, ...]


class _LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self.page_links: list[str] = []
        self.pdf_links: list[str] = []
        self.image_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            href = attributes.get("href")
            if href:
                resolved = urljoin(self._base_url, href)
                if _is_pdf(resolved):
                    self.pdf_links.append(resolved)
                else:
                    self.page_links.append(resolved)
        elif tag == "img":
            src = attributes.get("src")
            if src:
                self.image_links.append(urljoin(self._base_url, src))
        elif tag == "link":
            href = attributes.get("href")
            if href and _is_pdf(href):
                self.pdf_links.append(urljoin(self._base_url, href))


def extract_links(html: str, base_url: str) -> ExtractedLinks:
    """Extract absolute page, PDF and image links from an HTML fragment."""
    parser = _LinkParser(base_url)
    parser.feed(html)
    parser.close()
    return ExtractedLinks(
        page_links=_dedupe(parser.page_links),
        pdf_links=_dedupe(parser.pdf_links),
        image_links=_dedupe(parser.image_links),
    )


def doc_type_for(url: str, content_type: str = "") -> DocType:
    """Classify a fetched resource from its URL and content type."""
    lowered_type = content_type.lower()
    if _is_pdf(url) or "pdf" in lowered_type:
        return DocType.PDF
    path = urlsplit(url).path.lower()
    if "html" in lowered_type or path in {"", "/"} or path.endswith(_PAGE_SUFFIXES):
        return DocType.WEB_PAGE
    return DocType.OTHER
