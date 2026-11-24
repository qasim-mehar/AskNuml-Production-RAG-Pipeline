"""Main-content extraction heuristic: keep text, drop chrome (L9)."""

from dataclasses import dataclass
from html.parser import HTMLParser

_SKIP_TAGS = frozenset({"script", "style", "nav", "footer", "header", "aside", "form", "noscript"})


@dataclass(frozen=True)
class MainContent:
    """The page title and the de-chromed body text."""

    title: str
    text: str


class _ContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        else:
            self.text_parts.append(data)


def extract_main_content(html: str) -> MainContent:
    """Return the title and whitespace-normalised text outside common chrome.

    Scripts, styles, navigation, headers, footers, asides and forms are
    dropped; every other text node is kept (L12 fixtures pin the exact shape).
    """
    parser = _ContentParser()
    parser.feed(html)
    parser.close()
    return MainContent(
        title=" ".join(" ".join(parser.title_parts).split()),
        text=" ".join(" ".join(parser.text_parts).split()),
    )
